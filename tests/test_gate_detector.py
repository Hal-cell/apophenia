"""Tests for the gate (Schmitt-trigger) detector."""

from __future__ import annotations

import numpy as np
import pytest

from synapse.analysis.gate import GateDetector


def _block(n_channels: int, n_samples: int, values: list[float]) -> np.ndarray:
    block = np.zeros((n_channels, n_samples), dtype=np.float32)
    for i, v in enumerate(values):
        block[i, :] = v
    return block


def test_starts_low() -> None:
    det = GateDetector([0])
    out = det.process(_block(2, 512, [0.0, 0.0]))
    assert out.states == [False]
    assert out.rising_edges == [False]
    assert out.falling_edges == [False]


def test_rises_above_high_threshold() -> None:
    det = GateDetector([0], high_threshold=0.5, low_threshold=0.3)
    out = det.process(_block(2, 512, [0.7, 0.0]))
    assert out.states == [True]
    assert out.rising_edges == [True]
    assert out.falling_edges == [False]


def test_falls_below_low_threshold() -> None:
    det = GateDetector([0], high_threshold=0.5, low_threshold=0.3)
    det.process(_block(2, 512, [0.7, 0.0]))  # rising
    out = det.process(_block(2, 512, [0.1, 0.0]))  # falling
    assert out.states == [False]
    assert out.rising_edges == [False]
    assert out.falling_edges == [True]


def test_hysteresis_holds_state_in_dead_zone() -> None:
    """A signal in (low_threshold, high_threshold) shouldn't change state."""
    det = GateDetector([0], high_threshold=0.5, low_threshold=0.3)
    # Rise above high.
    det.process(_block(2, 512, [0.7, 0.0]))
    # Drop into dead zone (between thresholds): should stay HIGH.
    out = det.process(_block(2, 512, [0.4, 0.0]))
    assert out.states == [True]
    assert out.rising_edges == [False]
    assert out.falling_edges == [False]
    # Rise back above high: still high, no spurious rising edge.
    out = det.process(_block(2, 512, [0.8, 0.0]))
    assert out.states == [True]
    assert out.rising_edges == [False]


def test_edge_only_fires_once() -> None:
    """Sustained high signal: rising edge fires only the first time."""
    det = GateDetector([0])
    out1 = det.process(_block(2, 512, [0.9, 0.0]))
    out2 = det.process(_block(2, 512, [0.9, 0.0]))
    out3 = det.process(_block(2, 512, [0.9, 0.0]))
    assert out1.rising_edges == [True]
    assert out2.rising_edges == [False]
    assert out3.rising_edges == [False]
    assert all(out.states == [True] for out in (out1, out2, out3))


def test_uses_peak_not_mean() -> None:
    """A short pulse within the block should still trigger even though
    the block-mean might be below threshold (Eurorack triggers can be
    ~2ms, much shorter than a 10ms block)."""
    det = GateDetector([0], high_threshold=0.5)
    block = np.zeros((2, 512), dtype=np.float32)
    # 10-sample pulse at the start of an otherwise-silent block.
    block[0, :10] = 1.0
    # Block mean = 10/512 × 1.0 = 0.02, far below threshold. But peak = 1.0.
    out = det.process(block)
    assert out.states == [True]
    assert out.rising_edges == [True]


def test_negative_pulses_also_trigger() -> None:
    """Schmitt uses |peak|, so a negative-going trigger also fires."""
    det = GateDetector([0], high_threshold=0.5)
    block = np.zeros((2, 512), dtype=np.float32)
    block[0, :10] = -0.9
    out = det.process(block)
    assert out.states == [True]
    assert out.rising_edges == [True]


def test_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError):
        GateDetector([0], high_threshold=0.3, low_threshold=0.5)


def test_independent_channels() -> None:
    """Two configured gates should track independently."""
    det = GateDetector([0, 2])
    block = _block(4, 512, [0.9, 0.0, 0.0, 0.0])  # only ch0 fires
    out = det.process(block)
    assert out.states == [True, False]
    assert out.rising_edges == [True, False]
    assert out.channel_indices == [0, 2]


def test_empty_channels_returns_empty() -> None:
    det = GateDetector([])
    out = det.process(np.zeros((4, 512), dtype=np.float32))
    assert out.states == []
    assert out.rising_edges == []
    assert out.falling_edges == []
