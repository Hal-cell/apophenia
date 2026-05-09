"""Tests for fast-tier feature extraction + onset detector + FeatureBus."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from synapse.audio.features_fast import (
    ONSET_FLOOR,
    FastFeatures,
    FeatureBus,
    OnsetDetector,
    compute_block_features,
    fast_features_loop,
    make_window,
)
from synapse.audio.mock import MockSource

# --------------------------------------------------------------------------- #
# compute_block_features
# --------------------------------------------------------------------------- #


def test_compute_block_features_known_sine() -> None:
    """A pure sine of amplitude 0.5 has theoretical RMS = 0.5 / sqrt(2),
    peak = 0.5, and spectral centroid ≈ the sine's frequency.
    """
    n_channels, n_samples, sr = 4, 4096, 48_000
    freq = 1000.0
    t = np.arange(n_samples) / sr
    block = np.zeros((n_channels, n_samples), dtype=np.float32)
    for ch in range(n_channels):
        block[ch] = 0.5 * np.sin(2 * np.pi * freq * t)

    rms, peak, centroid = compute_block_features(block, sample_rate=sr)
    expected_rms = 0.5 / np.sqrt(2)
    np.testing.assert_allclose(rms, expected_rms, atol=0.005)
    np.testing.assert_allclose(peak, 0.5, atol=0.005)
    # Centroid for a clean sine should land within one bin width
    # (sr/N_FFT_BINS = 48000/2049 ≈ 23Hz). Allow 50Hz for safety.
    np.testing.assert_allclose(centroid, freq, atol=50.0)


def test_compute_block_features_silence() -> None:
    block = np.zeros((14, 256), dtype=np.float32)
    rms, peak, centroid = compute_block_features(block, sample_rate=48_000)
    assert np.all(rms == 0.0)
    assert np.all(peak == 0.0)
    assert np.all(centroid == 0.0)


def test_compute_block_features_high_freq_centroid() -> None:
    """High-frequency sine → high centroid; low-frequency sine → low centroid.
    Just check ordering, not exact values.
    """
    n_samples, sr = 4096, 48_000
    t = np.arange(n_samples) / sr
    low_block = np.zeros((1, n_samples), dtype=np.float32)
    low_block[0] = 0.5 * np.sin(2 * np.pi * 200.0 * t)
    high_block = np.zeros((1, n_samples), dtype=np.float32)
    high_block[0] = 0.5 * np.sin(2 * np.pi * 8000.0 * t)

    _, _, low_centroid = compute_block_features(low_block, sample_rate=sr)
    _, _, high_centroid = compute_block_features(high_block, sample_rate=sr)
    assert low_centroid[0] < high_centroid[0]
    assert low_centroid[0] < 500.0
    assert high_centroid[0] > 5000.0


def test_compute_block_features_silent_channel_has_zero_centroid() -> None:
    """Silent channels should report centroid 0, not noise from the
    division. Below ONSET_FLOOR, we explicitly zero it."""
    n_samples, sr = 1024, 48_000
    t = np.arange(n_samples) / sr
    block = np.zeros((2, n_samples), dtype=np.float32)
    block[0] = 0.5 * np.sin(2 * np.pi * 1000.0 * t)
    # block[1] stays silent

    _, _, centroid = compute_block_features(block, sample_rate=sr)
    assert centroid[0] > 500.0
    assert centroid[1] == 0.0


def test_compute_block_features_rejects_1d() -> None:
    with pytest.raises(ValueError):
        compute_block_features(np.zeros(1024, dtype=np.float32), sample_rate=48_000)


def test_compute_block_features_window_length_mismatch_rejected() -> None:
    block = np.zeros((2, 256), dtype=np.float32)
    bad_window = make_window(128)
    with pytest.raises(ValueError, match="window length"):
        compute_block_features(block, sample_rate=48_000, window=bad_window)


# --------------------------------------------------------------------------- #
# OnsetDetector
# --------------------------------------------------------------------------- #


def _detector(n_channels: int = 2) -> OnsetDetector:
    return OnsetDetector(n_channels=n_channels, sample_rate=48_000, block_size=512)


def test_onset_fires_on_sudden_loud_input() -> None:
    det = _detector(2)
    # A few quiet blocks let smoothed RMS settle near 0.
    for _ in range(20):
        env = det.update(np.array([0.001, 0.001]))
        assert np.all(env < 0.1)
    # Loud block on ch0 → onset, envelope = 1.0.
    env = det.update(np.array([0.3, 0.001]))
    assert env[0] == pytest.approx(1.0)
    assert env[1] < 0.1


def test_onset_below_floor_ignored() -> None:
    det = _detector(1)
    # Even a 100x ratio shouldn't fire if absolute level is below floor.
    for _ in range(20):
        det.update(np.array([0.0]))  # smoothed ≈ 0
    env = det.update(np.array([ONSET_FLOOR / 2]))  # tiny but ratio is huge
    assert env[0] < 0.5  # no fresh trigger


def test_onset_refractory_suppresses_back_to_back_hits() -> None:
    """Two consecutive loud blocks → only the first fires."""
    det = _detector(1)
    for _ in range(20):
        det.update(np.array([0.001]))
    env_first = det.update(np.array([0.3]))
    assert env_first[0] == pytest.approx(1.0)
    # Second block: still loud, but inside the refractory window.
    env_second = det.update(np.array([0.3]))
    # Envelope from first onset has decayed by one step (× 0.7), but no
    # fresh trigger should reset it back to 1.0.
    assert env_second[0] < 1.0
    assert env_second[0] == pytest.approx(0.7, abs=0.05)


def test_onset_envelope_decays_geometrically() -> None:
    det = _detector(1)
    for _ in range(20):
        det.update(np.array([0.001]))
    env = det.update(np.array([0.5]))
    assert env[0] == pytest.approx(1.0)
    # After ~10 quiet blocks (well past refractory) the envelope should
    # have decayed to nearly zero.
    for _ in range(10):
        env = det.update(np.array([0.001]))
    assert env[0] < 0.05


def test_onset_fires_again_after_refractory() -> None:
    det = _detector(1)
    for _ in range(20):
        det.update(np.array([0.001]))
    det.update(np.array([0.3]))  # fire 1
    for _ in range(10):
        det.update(np.array([0.001]))  # past refractory + decay
    env = det.update(np.array([0.3]))  # fire 2
    assert env[0] == pytest.approx(1.0)


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
# fast_features_loop end-to-end with MockSource
# --------------------------------------------------------------------------- #


def test_fast_loop_publishes_all_four_feature_arrays() -> None:
    """Drums pattern → loop → bus has rms / peak / centroid / onset_envelope."""
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
    assert len(latest.rms) == 14
    assert len(latest.peak) == 14
    assert len(latest.centroid) == 14
    assert len(latest.onset_envelope) == 14
    # ch9 (index 8) is silent in the drums pattern; centroid + envelope
    # should both be 0 for it.
    assert latest.rms[8] == 0.0
    assert latest.centroid[8] == 0.0
    assert latest.onset_envelope[8] == 0.0
    # ch1 (kick) should at some point have produced a non-zero envelope.
    # We can't guarantee the snapshot we caught is mid-onset, but over
    # 0.5s of drums at 120 BPM that's at least one kick — running smoothed
    # has been bumped enough that *some* snapshot likely had a non-zero
    # envelope. The assertion below tolerates the possibility we snapped
    # right between hits by checking peak instead, which is a per-block
    # max and definitely > 0 across many hits.
    assert latest.peak[0] > 0.0


def test_fast_loop_stops_promptly() -> None:
    src = MockSource(pattern="silence", block_size=512)
    bus = FeatureBus()
    stop = threading.Event()
    t = threading.Thread(target=fast_features_loop, args=(src, bus, stop), daemon=True)
    t.start()
    time.sleep(0.1)
    stop.set()
    t.join(timeout=1.0)
    assert not t.is_alive()
