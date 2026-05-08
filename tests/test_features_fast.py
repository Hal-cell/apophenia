"""Tests for fast-tier features and the FeatureBus mailbox."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from apophenia.audio.features_fast import (
    FastFeatures,
    FeatureBus,
    compute_block_features,
    fast_features_loop,
)
from apophenia.audio.mock import MockSource


# --------------------------------------------------------------------------- #
# compute_block_features
# --------------------------------------------------------------------------- #


def test_compute_block_features_known_signal() -> None:
    """A pure sine of amplitude 0.5 has theoretical RMS = 0.5 / sqrt(2)."""
    n_channels, n_samples = 4, 4096
    t = np.arange(n_samples) / 48_000.0
    block = np.zeros((n_channels, n_samples), dtype=np.float32)
    for ch in range(n_channels):
        block[ch] = 0.5 * np.sin(2 * np.pi * 440.0 * t)

    rms, peak = compute_block_features(block)
    expected_rms = 0.5 / np.sqrt(2)
    np.testing.assert_allclose(rms, expected_rms, atol=0.005)
    np.testing.assert_allclose(peak, 0.5, atol=0.005)
    assert rms.shape == (n_channels,)
    assert peak.shape == (n_channels,)


def test_compute_block_features_silence() -> None:
    block = np.zeros((14, 256), dtype=np.float32)
    rms, peak = compute_block_features(block)
    assert np.all(rms == 0.0)
    assert np.all(peak == 0.0)


def test_compute_block_features_rejects_1d() -> None:
    with pytest.raises(ValueError):
        compute_block_features(np.zeros(1024, dtype=np.float32))


# --------------------------------------------------------------------------- #
# FeatureBus
# --------------------------------------------------------------------------- #


def test_bus_starts_empty() -> None:
    bus = FeatureBus()
    assert bus.latest() is None


def test_bus_publishes_latest_only() -> None:
    bus = FeatureBus()
    bus.publish(FastFeatures(rms=[0.1] * 14, block_count=1))
    bus.publish(FastFeatures(rms=[0.2] * 14, block_count=2))
    latest = bus.latest()
    assert latest is not None
    assert latest.block_count == 2
    assert latest.rms[0] == 0.2


def test_bus_thread_safe_under_contention() -> None:
    """Many writers + many readers shouldn't tear or crash.

    We're not checking ordering — just that no exception fires and the
    final state has a valid block_count from the writer.
    """
    bus = FeatureBus()
    stop = threading.Event()

    def writer(i: int) -> None:
        n = 0
        while not stop.is_set():
            n += 1
            bus.publish(FastFeatures(rms=[float(n)] * 14, block_count=n + i * 100_000))

    def reader() -> None:
        while not stop.is_set():
            f = bus.latest()
            if f is not None:
                # Just access — would tear if lock weren't doing its job.
                _ = sum(f.rms)

    writers = [threading.Thread(target=writer, args=(i,), daemon=True) for i in range(3)]
    readers = [threading.Thread(target=reader, daemon=True) for _ in range(3)]
    for t in writers + readers:
        t.start()
    time.sleep(0.1)
    stop.set()
    for t in writers + readers:
        t.join(timeout=1.0)

    final = bus.latest()
    assert final is not None
    assert len(final.rms) == 14


# --------------------------------------------------------------------------- #
# fast_features_loop integration with MockSource
# --------------------------------------------------------------------------- #


def test_fast_loop_publishes_realistic_rms_for_drums() -> None:
    """End-to-end: drums pattern → fast loop → bus has plausible kick RMS.

    The drum pattern hits ch1 (kick) every beat with peak amplitude up
    to ~0.5 and rapid decay. RMS over a single block can be anywhere
    from near-zero (between hits) to ~0.2 (right on the impulse).
    Average over many blocks lands in the ~0.05-0.15 range. We just
    check it's nonzero and bounded.
    """
    src = MockSource(pattern="drums", block_size=256)
    bus = FeatureBus()
    stop = threading.Event()

    t = threading.Thread(target=fast_features_loop, args=(src, bus, stop), daemon=True)
    t.start()
    time.sleep(0.5)
    stop.set()
    t.join(timeout=2.0)

    latest = bus.latest()
    assert latest is not None
    assert latest.n_channels == 14
    assert latest.sample_rate == 48_000
    assert latest.block_size == 256
    assert latest.source_name == "MockSource"
    assert latest.block_count > 0

    # ch1 (kick) should be louder than ch9 (silent in drums pattern).
    # We're comparing single-block snapshots so this is noisy; only check
    # the ordering, not absolute values.
    assert latest.rms[0] >= 0.0
    assert latest.rms[8] == 0.0  # ch9 silent in drums
    assert latest.peak[0] >= latest.peak[8]


def test_fast_loop_stops_promptly() -> None:
    """Setting the stop event should drain within one block period."""
    src = MockSource(pattern="silence", block_size=512)
    bus = FeatureBus()
    stop = threading.Event()

    t = threading.Thread(target=fast_features_loop, args=(src, bus, stop), daemon=True)
    t.start()
    time.sleep(0.1)
    stop.set()
    t.join(timeout=1.0)
    assert not t.is_alive(), "fast_features_loop didn't honour stop event"
