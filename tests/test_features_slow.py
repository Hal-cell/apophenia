"""Tests for the slow-tier (CLAP) feature pipeline.

Real CLAP inference downloads ~600MB and takes seconds; we don't run it
in CI. These tests cover the plumbing — AudioBuffer ring semantics,
SlowBus thread-safety, slow_features_loop wiring through a stub
encoder — and leave the real-model run to manual smoke tests.

A `@pytest.mark.skipif` test calling the real `ClapEncoder.load()` is
included for completeness but skipped unless `SYNAPSE_RUN_CLAP=1` is
set in the environment.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

import numpy as np
import pytest

from synapse.audio.features_slow import (
    CLAP_EMBED_DIM,
    AudioBuffer,
    SlowBus,
    SlowFeatures,
    slow_features_loop,
)

# --------------------------------------------------------------------------- #
# AudioBuffer
# --------------------------------------------------------------------------- #


def test_audio_buffer_basic_write_and_tail() -> None:
    buf = AudioBuffer(n_channels=2, sample_rate=1000, duration_s=1.0)  # 1000 samples
    block = np.tile(np.arange(100, dtype=np.float32), (2, 1))  # (2, 100), values 0..99
    buf.write(block)
    tail = buf.tail(100)
    assert tail.shape == (2, 100)
    np.testing.assert_array_equal(tail, block)


def test_audio_buffer_wraparound() -> None:
    """Writing more samples than the buffer holds + reading should
    return the most recent N samples in chronological order."""
    cap = 1000
    buf = AudioBuffer(n_channels=1, sample_rate=cap, duration_s=1.0)
    # Write 1500 samples in two writes to force a wraparound.
    block_a = np.arange(0, 800, dtype=np.float32).reshape(1, -1)
    block_b = np.arange(800, 1500, dtype=np.float32).reshape(1, -1)
    buf.write(block_a)
    buf.write(block_b)
    tail = buf.tail(500)
    # The most recent 500 samples are 1000..1499.
    np.testing.assert_array_equal(tail, np.arange(1000, 1500, dtype=np.float32).reshape(1, -1))


def test_audio_buffer_rejects_oversized_block() -> None:
    buf = AudioBuffer(n_channels=2, sample_rate=100, duration_s=0.5)  # 50 samples
    with pytest.raises(ValueError):
        buf.write(np.zeros((2, 100), dtype=np.float32))


def test_audio_buffer_rejects_wrong_channel_count() -> None:
    buf = AudioBuffer(n_channels=2, sample_rate=100, duration_s=1.0)
    with pytest.raises(ValueError):
        buf.write(np.zeros((3, 50), dtype=np.float32))


def test_audio_buffer_tail_too_large_rejected() -> None:
    buf = AudioBuffer(n_channels=1, sample_rate=100, duration_s=1.0)
    with pytest.raises(ValueError):
        buf.tail(500)


def test_audio_buffer_thread_safe() -> None:
    """Concurrent writers + readers shouldn't tear or crash."""
    buf = AudioBuffer(n_channels=4, sample_rate=4000, duration_s=1.0)
    stop = threading.Event()
    errors: list[Exception] = []

    def writer() -> None:
        block = np.ones((4, 256), dtype=np.float32)
        try:
            while not stop.is_set():
                buf.write(block)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def reader() -> None:
        try:
            while not stop.is_set():
                _ = buf.tail(1024)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ws = [threading.Thread(target=writer, daemon=True) for _ in range(2)]
    rs = [threading.Thread(target=reader, daemon=True) for _ in range(2)]
    for t in ws + rs:
        t.start()
    time.sleep(0.1)
    stop.set()
    for t in ws + rs:
        t.join(timeout=1.0)
    assert not errors, f"thread errors: {errors}"


# --------------------------------------------------------------------------- #
# SlowBus
# --------------------------------------------------------------------------- #


def test_slow_bus_starts_empty() -> None:
    bus = SlowBus()
    assert bus.latest() is None


def test_slow_bus_publish_replace() -> None:
    bus = SlowBus()
    bus.publish(SlowFeatures(clap_embedding=[0.1] * CLAP_EMBED_DIM, update_count=1))
    bus.publish(SlowFeatures(clap_embedding=[0.2] * CLAP_EMBED_DIM, update_count=2))
    latest = bus.latest()
    assert latest is not None
    assert latest.update_count == 2
    assert latest.clap_embedding[0] == pytest.approx(0.2)


# --------------------------------------------------------------------------- #
# slow_features_loop with a mock encoder
# --------------------------------------------------------------------------- #


@dataclass
class _StubSource:
    n_channels: int
    sample_rate: int
    block_size: int


class _MockEncoder:
    """Stand-in for ClapEncoder. Returns a deterministic vector each call,
    fast (no model load), so tests don't need torch / transformers. The
    only contract slow_features_loop expects is `.encode(mono, sr) →
    (CLAP_EMBED_DIM,) ndarray` and a `.model_name` string.
    """

    def __init__(self) -> None:
        self.calls = 0
        self.model_name = "stub/mock-encoder"

    def encode(self, audio_mono: np.ndarray, sample_rate: int) -> np.ndarray:
        self.calls += 1
        # Embedding magnitude rises with audio RMS so we can verify the
        # worker is feeding fresh data each call.
        rms = float(np.sqrt(np.mean(audio_mono.astype(np.float64) ** 2)))
        return np.full(CLAP_EMBED_DIM, rms, dtype=np.float32)


def test_slow_loop_publishes_via_mock_encoder() -> None:
    src = _StubSource(n_channels=2, sample_rate=48_000, block_size=512)
    buf = AudioBuffer(n_channels=2, sample_rate=48_000, duration_s=2.0)
    # Pre-fill with non-zero audio so the slow worker doesn't bail at startup.
    buf.write(np.full((2, 48_000 * 2), 0.5, dtype=np.float32))
    bus = SlowBus()
    enc = _MockEncoder()
    stop = threading.Event()

    t = threading.Thread(
        target=slow_features_loop,
        args=(src, buf, bus, stop, enc),
        kwargs={"period_s": 0.05, "window_s": 1.0},
        daemon=True,
    )
    t.start()
    # Give the worker time for at least 2 inference cycles at 50ms period.
    time.sleep(0.25)
    stop.set()
    t.join(timeout=1.0)

    latest = bus.latest()
    assert latest is not None
    assert enc.calls >= 2
    assert latest.update_count >= 2
    assert len(latest.clap_embedding) == CLAP_EMBED_DIM
    # Mock encoder fills the vector with the input RMS, which is 0.5.
    assert latest.clap_embedding[0] == pytest.approx(0.5, abs=0.01)
    assert latest.embedding_norm == pytest.approx(0.5 * (CLAP_EMBED_DIM**0.5), rel=0.01)
    assert latest.model_name == "stub/mock-encoder"


def test_slow_loop_waits_for_buffer_to_fill() -> None:
    """Without pre-fill, the slow worker should sit idle until enough
    audio has arrived. We verify by leaving the buffer empty for a moment
    then writing one full window."""
    src = _StubSource(n_channels=1, sample_rate=4_000, block_size=128)
    buf = AudioBuffer(n_channels=1, sample_rate=4_000, duration_s=2.0)
    bus = SlowBus()
    enc = _MockEncoder()
    stop = threading.Event()

    t = threading.Thread(
        target=slow_features_loop,
        args=(src, buf, bus, stop, enc),
        kwargs={"period_s": 0.05, "window_s": 0.5},
        daemon=True,
    )
    t.start()

    # 100ms with empty buffer → no inference should have run.
    time.sleep(0.1)
    assert enc.calls == 0
    assert bus.latest() is None

    # Now feed one window's worth of audio.
    buf.write(np.full((1, 2_000), 0.3, dtype=np.float32))
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1.0)
    assert enc.calls >= 1
    assert bus.latest() is not None


# --------------------------------------------------------------------------- #
# Real CLAP — opt-in
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    os.environ.get("SYNAPSE_RUN_CLAP") != "1",
    reason="set SYNAPSE_RUN_CLAP=1 to run the real CLAP model (downloads ~600MB)",
)
def test_real_clap_encoder_loads_and_encodes() -> None:
    """Sanity check the actual HuggingFace CLAP can load + run on this
    machine. Skipped by default; opt in with SYNAPSE_RUN_CLAP=1.
    """
    from synapse.audio.features_slow import ClapEncoder

    enc = ClapEncoder()
    enc.load()
    audio = np.random.randn(48_000).astype(np.float32) * 0.1  # 1s noise
    embed = enc.encode(audio, 48_000)
    assert embed.shape == (CLAP_EMBED_DIM,)
    assert np.isfinite(embed).all()
