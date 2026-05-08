"""Tests for the ai_loop background worker.

Real SDXL inference downloads ~5GB and takes ~10s per call on M3 Max; we
don't run it in CI. These tests cover the plumbing — StateBus reads,
AIBus publishes, freeze handling, exception isolation — using a stub
generator. A `@pytest.mark.skipif` test that drives the real
SDXLTurboGenerator is included for completeness, gated on
`APOPHENIA_RUN_SDXL=1`.
"""

from __future__ import annotations

import os
import threading
import time

import numpy as np
import pytest

from apophenia.ai.bus import AIBus
from apophenia.ai.loop import ai_loop
from apophenia.control.state_bus import StateBus


class _MockGenerator:
    """Returns a constant gradient so each call's bytes are identical;
    we only care about call count + plumbing here, not pixels."""

    def __init__(self, latency_s: float = 0.0) -> None:
        self.calls = 0
        self.latency_s = latency_s
        self.model_name = "stub/sdxl-turbo-mock"
        self._img = np.zeros((32, 32, 3), dtype=np.uint8)

    def generate(
        self,
        prompt: str,
        seed: int | None = None,
        num_inference_steps: int = 1,
        guidance_scale: float = 0.0,
        resolution: int | None = None,
    ) -> np.ndarray:
        self.calls += 1
        if self.latency_s > 0:
            time.sleep(self.latency_s)
        # Encode the call count in the first pixel so tests can verify
        # ordering.
        img = self._img.copy()
        img[0, 0] = (self.calls % 256, 0, 0)
        return img


def test_ai_loop_publishes_frames() -> None:
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "abstract"}})
    bus = AIBus()
    gen = _MockGenerator(latency_s=0.01)
    stop = threading.Event()

    t = threading.Thread(target=ai_loop, args=(state_bus, bus, stop, gen), daemon=True)
    t.start()
    time.sleep(0.15)
    stop.set()
    t.join(timeout=1.0)

    latest = bus.latest()
    assert latest is not None
    assert gen.calls >= 2
    assert latest.gen_count == gen.calls
    assert latest.prompt == "abstract"
    assert latest.model_name == "stub/sdxl-turbo-mock"
    assert latest.latency_ms > 0


def test_ai_loop_skips_when_frozen() -> None:
    """transport.freeze=True → no inference happens."""
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "p"}, "transport": {"freeze": True}})
    bus = AIBus()
    gen = _MockGenerator()
    stop = threading.Event()

    t = threading.Thread(target=ai_loop, args=(state_bus, bus, stop, gen), daemon=True)
    t.start()
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1.0)

    assert gen.calls == 0
    assert bus.latest() is None


def test_ai_loop_resumes_after_unfreeze() -> None:
    """Unfreezing should let inference resume mid-loop."""
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "p"}, "transport": {"freeze": True}})
    bus = AIBus()
    gen = _MockGenerator(latency_s=0.005)
    stop = threading.Event()

    t = threading.Thread(target=ai_loop, args=(state_bus, bus, stop, gen), daemon=True)
    t.start()
    time.sleep(0.1)
    assert gen.calls == 0

    # Unfreeze.
    state_bus.update({"transport": {"freeze": False}})
    time.sleep(0.15)
    stop.set()
    t.join(timeout=1.0)

    assert gen.calls > 0
    latest = bus.latest()
    assert latest is not None


def test_ai_loop_skips_when_prompt_empty() -> None:
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "   "}})  # whitespace
    bus = AIBus()
    gen = _MockGenerator()
    stop = threading.Event()

    t = threading.Thread(target=ai_loop, args=(state_bus, bus, stop, gen), daemon=True)
    t.start()
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1.0)

    assert gen.calls == 0
    assert bus.latest() is None


def test_ai_loop_swallows_generator_exceptions() -> None:
    """A flaky generator must not kill the loop — log + continue."""

    class _Flaky:
        model_name = "flaky"

        def __init__(self) -> None:
            self.calls = 0

        def generate(
            self,
            prompt: str,
            seed: int | None = None,
            num_inference_steps: int = 1,
            guidance_scale: float = 0.0,
            resolution: int | None = None,
        ) -> np.ndarray:
            self.calls += 1
            if self.calls % 2 == 1:
                raise RuntimeError("random GPU OOM")
            return np.zeros((4, 4, 3), dtype=np.uint8)

    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "p"}})
    bus = AIBus()
    gen = _Flaky()
    stop = threading.Event()

    t = threading.Thread(
        target=ai_loop,
        args=(state_bus, bus, stop, gen),
        kwargs={"min_period_s": 0.0},
        daemon=True,
    )
    t.start()
    time.sleep(0.4)
    stop.set()
    t.join(timeout=1.0)

    # We should have at least one successful publish despite alternating
    # failures.
    assert bus.latest() is not None
    assert gen.calls >= 2


def test_ai_loop_min_period_throttles() -> None:
    """min_period_s caps the cycle rate from below."""
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "p"}})
    bus = AIBus()
    gen = _MockGenerator(latency_s=0.0)
    stop = threading.Event()

    t = threading.Thread(
        target=ai_loop,
        args=(state_bus, bus, stop, gen),
        kwargs={"min_period_s": 0.05},
        daemon=True,
    )
    t.start()
    time.sleep(0.25)
    stop.set()
    t.join(timeout=1.0)

    # 0.25s / 0.05s = 5 cycles max plus jitter; should NOT have hundreds.
    assert gen.calls < 10


@pytest.mark.skipif(
    os.environ.get("APOPHENIA_RUN_SDXL") != "1",
    reason="set APOPHENIA_RUN_SDXL=1 to run the real SDXL-Turbo (downloads ~5GB)",
)
def test_real_sdxl_generator_loads_and_renders() -> None:
    """Sanity check the actual HuggingFace SDXL-Turbo can load + run on this
    machine. Skipped by default; opt in with APOPHENIA_RUN_SDXL=1."""
    from apophenia.ai.sdxl_turbo import DEFAULT_RESOLUTION, SDXLTurboGenerator

    gen = SDXLTurboGenerator()
    gen.load()
    img = gen.generate("abstract liquid form", seed=42)
    assert img.dtype == np.uint8
    assert img.shape == (DEFAULT_RESOLUTION, DEFAULT_RESOLUTION, 3)
    # Output must contain non-trivial variation; an all-zero frame would
    # mean inference silently failed.
    assert img.std() > 5.0
