"""Background worker that drives `SDXLTurboGenerator` from the live state.

Cadence:
  * The renderer runs at 60+ fps; SDXL-Turbo on M3 Max generates at
    ~5–15 fps. The worker loops as fast as the generator allows, capped
    by `min_period_s` so we don't pin the GPU at 100% if the user
    deliberately wants slower turnover (e.g. for "tableau" effects).
  * Each cycle:
      1. read `state_bus.get()` for the live prompt + blend params
      2. (optional) read `slow_bus.latest()` for the CLAP embedding —
         in V1 we just use it for telemetry / future conditioning hooks
      3. invoke `generator.generate(prompt)` and time it
      4. publish the result to `ai_bus`
  * `transport.freeze` skips inference entirely — the most recent frame
    stays as-is, saving GPU cycles during the tableau.
  * Exceptions inside the inference call get logged and the loop carries
    on; we don't want a one-off CUDA OOM or shape mismatch to kill the
    whole tier.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Protocol

import numpy as np

from apophenia.ai.bus import AIBus, AIFrame

if TYPE_CHECKING:
    from apophenia.audio.features_slow import SlowBus
    from apophenia.control.state_bus import StateBus

logger = logging.getLogger(__name__)


class _Generator(Protocol):
    """Duck-typed view of `SDXLTurboGenerator`. Tests use a stub that
    matches this signature; the loop never imports the real class."""

    model_name: str

    def generate(
        self,
        prompt: str,
        seed: int | None = ...,
        num_inference_steps: int = ...,
        guidance_scale: float = ...,
        resolution: int | None = ...,
    ) -> np.ndarray: ...


def ai_loop(
    state_bus: StateBus,
    ai_bus: AIBus,
    stop_event: threading.Event,
    generator: _Generator,
    *,
    slow_bus: SlowBus | None = None,
    min_period_s: float = 0.0,
) -> None:
    """Drive `generator` from the StateBus and publish results to AIBus.

    Runs until `stop_event` is set. `min_period_s` is a *floor* on the
    cycle period — generations faster than this sleep the difference; the
    GPU is otherwise the rate limiter.
    """
    gen_count = 0
    while not stop_event.is_set():
        cycle_t0 = time.monotonic()

        state = state_bus.get()
        if state.transport.freeze:
            # Hold the previous frame; sleep a beat and check again.
            time.sleep(max(min_period_s, 0.05))
            continue

        prompt = state.text.prompt or ""
        if not prompt.strip():
            # Nothing to draw; back off briefly.
            time.sleep(max(min_period_s, 0.1))
            continue

        # Future hook: use slow_bus.latest().clap_embedding as conditioning.
        # V1 ships text-only and treats CLAP as a separate visual signal
        # (the heatmap / future audio-text blend at the embedding level).
        _ = slow_bus.latest() if slow_bus is not None else None

        seed = int(np.random.randint(0, 2**31 - 1))
        try:
            t0 = time.perf_counter()
            image = generator.generate(prompt, seed=seed)
            latency_ms = (time.perf_counter() - t0) * 1000.0
        except Exception:  # noqa: BLE001
            logger.exception("ai_loop: generator failed; skipping cycle")
            # Small cooldown after a failure so we don't pin the GPU
            # retrying a permanent error; long enough to log + breathe,
            # short enough that a transient hiccup recovers in <1 frame.
            time.sleep(max(min_period_s, 0.1))
            continue

        gen_count += 1
        frame = AIFrame(
            image=image,
            prompt=prompt,
            gen_count=gen_count,
            latency_ms=latency_ms,
            seed=seed,
            model_name=getattr(generator, "model_name", "unknown"),
        )
        ai_bus.publish(frame)

        # Back off if we're running faster than the requested floor.
        elapsed = time.monotonic() - cycle_t0
        if elapsed < min_period_s:
            time.sleep(min_period_s - elapsed)
