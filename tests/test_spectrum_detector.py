"""Tests for SpectrumDetector — log-spaced bins, throttling, sine localisation."""

from __future__ import annotations

import numpy as np
import pytest

from synapse.analysis.spectrum import SpectrumDetector, SpectrumFeatures

# --------------------------------------------------------------------------- #
# Construction + edge cases
# --------------------------------------------------------------------------- #


def test_bin_edges_log_spaced() -> None:
    """The bin edges should be geometrically spaced from fmin to nyquist."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=512,
        n_bins=8, fmin_hz=20.0,
    )
    assert len(det.bin_edges_hz) == 9  # n_bins + 1
    # Ratios between successive edges should be (nearly) constant.
    ratios = [det.bin_edges_hz[i + 1] / det.bin_edges_hz[i] for i in range(8)]
    np.testing.assert_allclose(ratios, ratios[0], rtol=1e-9)
    # Endpoints.
    assert det.bin_edges_hz[0] == pytest.approx(20.0)
    assert det.bin_edges_hz[-1] == pytest.approx(24000.0)


def test_throttle_stride_matches_target_hz() -> None:
    """At 48kHz/512 = ~94Hz block rate, target 30Hz → stride ≈ 3."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=512,
        output_hz=30.0,
    )
    assert det.stride == 3
    # Effective output rate is the actual achievable ratio.
    assert det.output_hz_effective == pytest.approx(48000 / 512 / 3, rel=1e-9)


def test_no_audio_channels_returns_none() -> None:
    det = SpectrumDetector(
        audio_channel_indices=[], sample_rate=48000, block_size=512,
    )
    block = np.zeros((4, 512), dtype=np.float32)
    assert det.process(block) is None


def test_rejects_bad_args() -> None:
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=0, block_size=512)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=0)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=512, n_bins=0)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=512, output_hz=0)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=512, fmin_hz=0)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=512, fmin_hz=30000.0)
    with pytest.raises(ValueError):
        SpectrumDetector([0], sample_rate=48000, block_size=512, compression=-1.0)


# --------------------------------------------------------------------------- #
# Throttling behaviour
# --------------------------------------------------------------------------- #


def test_emits_only_on_stride_boundaries() -> None:
    """At stride=3, the first 2 calls return None, the 3rd returns a frame."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=512,
        output_hz=30.0,  # stride = 3
    )
    block = np.zeros((4, 512), dtype=np.float32)
    assert det.process(block, 1) is None
    assert det.process(block, 2) is None
    frame = det.process(block, 3)
    assert isinstance(frame, SpectrumFeatures)
    # Next two are None again.
    assert det.process(block, 4) is None
    assert det.process(block, 5) is None
    # 6 emits.
    assert det.process(block, 6) is not None


def test_latest_returns_last_emitted_frame() -> None:
    """latest() is None until first emit, then sticks across throttled calls."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=512,
        output_hz=30.0,  # stride = 3
    )
    block = np.zeros((4, 512), dtype=np.float32)
    assert det.latest() is None
    # Two throttled calls.
    assert det.process(block, 1) is None
    assert det.latest() is None
    assert det.process(block, 2) is None
    assert det.latest() is None
    # Third call emits.
    frame = det.process(block, 3)
    assert isinstance(frame, SpectrumFeatures)
    assert det.latest() is frame
    # Two more throttled calls — latest stays the same frame.
    assert det.process(block, 4) is None
    assert det.latest() is frame
    assert det.process(block, 5) is None
    assert det.latest() is frame


# --------------------------------------------------------------------------- #
# Spectrum content: localisation
# --------------------------------------------------------------------------- #


def _sine_block(freq: float, sample_rate: int, block_size: int, n_channels: int = 1) -> np.ndarray:
    t = np.arange(block_size) / sample_rate
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    block = np.zeros((n_channels, block_size), dtype=np.float32)
    for ch in range(n_channels):
        block[ch] = sig
    return block


def test_low_freq_sine_lands_in_low_bin() -> None:
    """A 100Hz sine should put its energy in one of the lowest bins."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=2048,
        n_bins=32, output_hz=30.0, compression=0.0,
    )
    # Skip throttle by calling stride times.
    block = _sine_block(100.0, 48000, 2048)
    for _ in range(det.stride):
        out = det.process(block)
    assert isinstance(out, SpectrumFeatures)
    bins = np.array(out.bins[0])
    peak_bin = int(np.argmax(bins))
    # 100Hz with fmin=20, nyquist=24000, n_bins=32, log-spaced.
    # log(100/20) / log(24000/20) * 32 ≈ 7.4 — peak should be ~bin 7-9.
    assert 4 <= peak_bin <= 11, f"100Hz sine peaked in bin {peak_bin}, expected low"


def test_high_freq_sine_lands_in_high_bin() -> None:
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=2048,
        n_bins=32, output_hz=30.0, compression=0.0,
    )
    block = _sine_block(8000.0, 48000, 2048)
    for _ in range(det.stride):
        out = det.process(block)
    assert isinstance(out, SpectrumFeatures)
    bins = np.array(out.bins[0])
    peak_bin = int(np.argmax(bins))
    assert peak_bin >= 22, f"8kHz sine peaked in bin {peak_bin}, expected high"


def test_silent_block_yields_near_zero_bins() -> None:
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=512,
        n_bins=32, output_hz=30.0, compression=0.0,
    )
    block = np.zeros((4, 512), dtype=np.float32)
    for _ in range(det.stride):
        out = det.process(block)
    assert isinstance(out, SpectrumFeatures)
    bins = np.array(out.bins[0])
    assert bins.max() < 1e-9


# --------------------------------------------------------------------------- #
# Channel selection
# --------------------------------------------------------------------------- #


def test_only_audio_channels_in_output() -> None:
    """A 4-channel block, but only channels [1, 3] are configured as audio."""
    det = SpectrumDetector(
        audio_channel_indices=[1, 3], sample_rate=48000, block_size=2048,
        n_bins=16, output_hz=30.0, compression=0.0,
    )
    # Put a sine on ch1, silence on ch3, garbage on the others.
    block = np.zeros((4, 2048), dtype=np.float32)
    t = np.arange(2048) / 48000
    block[0] = 0.3  # DC, NOT in audio set
    block[1] = 0.5 * np.sin(2 * np.pi * 1000.0 * t)
    block[2] = np.random.randn(2048).astype(np.float32) * 0.5  # noise, NOT audio
    # block[3] stays silent

    for _ in range(det.stride):
        out = det.process(block)
    assert out is not None
    assert out.channel_indices == [1, 3]
    assert len(out.bins) == 2
    # ch1 (index 0 in output): should have peak energy from the sine
    assert max(out.bins[0]) > 0.0
    # ch3 (index 1 in output): silent → near zero
    assert max(out.bins[1]) < 1e-9


# --------------------------------------------------------------------------- #
# Compression
# --------------------------------------------------------------------------- #


def test_compression_caps_bins_at_one() -> None:
    """With heavy compression, bin values should saturate near 1.0 for loud input."""
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=2048,
        n_bins=32, output_hz=30.0, compression=8.0,
    )
    block = _sine_block(1000.0, 48000, 2048)
    for _ in range(det.stride):
        out = det.process(block)
    assert out is not None
    bins = np.array(out.bins[0])
    # tanh saturates at 1, so peak bin should be < 1 but pushed up.
    assert bins.max() < 1.0
    assert bins.max() > 0.0


def test_no_compression_returns_raw_magnitude() -> None:
    det = SpectrumDetector(
        audio_channel_indices=[0], sample_rate=48000, block_size=2048,
        n_bins=32, output_hz=30.0, compression=0.0,
    )
    block = _sine_block(1000.0, 48000, 2048)
    for _ in range(det.stride):
        out = det.process(block)
    assert out is not None
    # Without tanh, magnitude can be anything > 0; just check non-zero.
    bins = np.array(out.bins[0])
    assert bins.max() > 0.0
