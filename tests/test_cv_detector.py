"""Tests for the CV detector — IIR low-pass extraction of slow DC values."""

from __future__ import annotations

import math

import numpy as np
import pytest

from synapse.analysis.cv import CVDetector


def _block(n_channels: int, n_samples: int, values: list[float]) -> np.ndarray:
    """Build a `(n_channels, n_samples)` block where channel i is filled
    with `values[i]` (constant DC). Other channels stay zero."""
    block = np.zeros((n_channels, n_samples), dtype=np.float32)
    for i, v in enumerate(values):
        block[i, :] = v
    return block


def test_empty_channels_returns_empty_features() -> None:
    det = CVDetector([], block_rate_hz=94.0)
    out = det.process(np.zeros((4, 512), dtype=np.float32))
    assert out.values == []
    assert out.rates == []
    assert out.channel_indices == []


def test_iir_converges_on_constant_dc() -> None:
    """Feeding the same DC value many blocks should converge value→DC."""
    det = CVDetector([0], block_rate_hz=94.0, cutoff_hz=10.0)
    block = _block(2, 512, [0.5, 0.0])
    # Iterate; smoothed value should approach 0.5.
    for _ in range(200):
        out = det.process(block)
    assert abs(out.values[0] - 0.5) < 0.01


def test_iir_responds_to_step() -> None:
    """A step from 0 → 1 should make the output rise."""
    det = CVDetector([0], block_rate_hz=94.0, cutoff_hz=10.0)
    # Settle on 0.
    zero_block = _block(2, 512, [0.0, 0.0])
    for _ in range(50):
        det.process(zero_block)
    initial = det.process(zero_block).values[0]
    # Step input.
    step_block = _block(2, 512, [1.0, 0.0])
    after_one = det.process(step_block).values[0]
    after_many = initial
    for _ in range(50):
        after_many = det.process(step_block).values[0]
    assert initial < 0.05  # essentially 0
    assert after_one > initial  # responded
    assert after_many > 0.95   # converged


def test_rate_positive_during_rise() -> None:
    """Rate-of-change should be positive while value is increasing."""
    det = CVDetector([0], block_rate_hz=94.0, cutoff_hz=10.0)
    zero_block = _block(2, 512, [0.0, 0.0])
    for _ in range(20):
        det.process(zero_block)
    step_block = _block(2, 512, [1.0, 0.0])
    # Sample mid-rise.
    rates: list[float] = []
    for _ in range(15):
        out = det.process(step_block)
        rates.append(out.rates[0])
    # Most rates during the rise should be positive.
    assert sum(1 for r in rates if r > 0) >= 12


def test_rate_decays_after_step() -> None:
    """Rate-of-change should decay back toward 0 after the value has
    settled at the new DC."""
    det = CVDetector([0], block_rate_hz=94.0, cutoff_hz=10.0)
    step_block = _block(2, 512, [0.5, 0.0])
    for _ in range(500):
        det.process(step_block)
    out = det.process(step_block)
    assert abs(out.rates[0]) < 0.1


def test_alpha_calculation() -> None:
    """Sanity check the IIR coefficient: α = 1 − exp(−2π · f_c / f_s)."""
    det = CVDetector([0], block_rate_hz=94.0, cutoff_hz=10.0)
    expected = 1.0 - math.exp(-2.0 * math.pi * 10.0 / 94.0)
    assert det.alpha == pytest.approx(expected)


def test_rejects_invalid_block_rate() -> None:
    with pytest.raises(ValueError):
        CVDetector([0], block_rate_hz=0)
    with pytest.raises(ValueError):
        CVDetector([0], block_rate_hz=-10.0)


def test_rejects_invalid_cutoff() -> None:
    # Above Nyquist of block rate → unstable.
    with pytest.raises(ValueError):
        CVDetector([0], block_rate_hz=94.0, cutoff_hz=50.0)
    with pytest.raises(ValueError):
        CVDetector([0], block_rate_hz=94.0, cutoff_hz=-1.0)


def test_independent_channels_dont_cross_contaminate() -> None:
    """Two channels with different DC values should track independently."""
    det = CVDetector([0, 2], block_rate_hz=94.0, cutoff_hz=10.0)
    block = _block(4, 512, [0.5, 0.0, -0.3, 0.0])
    for _ in range(300):
        out = det.process(block)
    assert abs(out.values[0] - 0.5) < 0.01
    assert abs(out.values[1] - (-0.3)) < 0.01
    assert out.channel_indices == [0, 2]
