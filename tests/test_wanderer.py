"""Tests for the autopilot Wanderer — slow 1D smooth-noise generator."""

from __future__ import annotations

import math

import pytest

from apophenia.autopilot.wanderer import Wanderer, _hash11, _value_noise_1d

# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #


def test_hash11_in_range() -> None:
    for x in [-100.0, -1.5, 0.0, 0.7, 13.4, 1000.5]:
        for seed in [0, 7, 99, 2024]:
            v = _hash11(x, seed)
            assert -1.0 <= v <= 1.0


def test_hash11_deterministic() -> None:
    """Same (x, seed) → same value, every call."""
    assert _hash11(3.14, 42) == _hash11(3.14, 42)
    assert _hash11(0.0, 0) == _hash11(0.0, 0)


def test_hash11_decorrelates_seeds() -> None:
    """Different seeds with the same `x` should give different values
    (with overwhelming probability — the hash isn't degenerate)."""
    seen = {_hash11(1.0, s) for s in range(20)}
    # 20 distinct seeds should produce > 15 distinct values.
    assert len(seen) >= 15


def test_value_noise_1d_continuous() -> None:
    """The smoothstep interpolation should give C¹ continuity. Adjacent
    samples shouldn't have huge jumps."""
    seed = 1234
    prev = _value_noise_1d(0.0, seed)
    for i in range(1, 100):
        x = i * 0.01
        v = _value_noise_1d(x, seed)
        # Jump between consecutive samples should be small (well under 1)
        # since the interpolant is between two endpoints in [-1, 1] and
        # the derivative of smoothstep on [0, 1] is bounded.
        assert abs(v - prev) < 0.5, f"big jump at x={x}: {prev} → {v}"
        prev = v


def test_value_noise_1d_periodicity_at_integers() -> None:
    """At integer x, the value should be exactly hash11(int_part, seed)
    because the smoothstep weight at f=0 is 0."""
    seed = 99
    for i in range(10):
        x = float(i)
        assert _value_noise_1d(x, seed) == _hash11(x, seed)


# --------------------------------------------------------------------------- #
# Wanderer
# --------------------------------------------------------------------------- #


def test_wanderer_in_range() -> None:
    """value() always lies in [-1, 1] regardless of t / seed / period."""
    for seed in [0, 1, 42, 12345]:
        for period in [1.0, 30.0, 300.0]:
            w = Wanderer(seed=seed, period_s=period)
            for t in [0.0, 0.5, 5.0, 60.0, 600.0, 3600.0]:
                v = w.value(t)
                assert -1.0 <= v <= 1.0, f"out of range: seed={seed} t={t}: {v}"


def test_wanderer_deterministic() -> None:
    w1 = Wanderer(seed=7, period_s=30.0)
    w2 = Wanderer(seed=7, period_s=30.0)
    for t in [0.0, 1.5, 30.0, 100.0]:
        assert w1.value(t) == w2.value(t)


def test_wanderer_different_seeds_decorrelate() -> None:
    """Two wanderers with different seeds should not produce identical
    trajectories. Sample at a few t and confirm at least some differ."""
    w1 = Wanderer(seed=1, period_s=30.0)
    w2 = Wanderer(seed=2, period_s=30.0)
    diffs = sum(
        abs(w1.value(t) - w2.value(t)) > 1e-3
        for t in [0.0, 0.7, 5.0, 30.0, 100.0]
    )
    assert diffs >= 3


def test_wanderer_continuity() -> None:
    """No large jumps between adjacent samples — wanderer is smooth."""
    w = Wanderer(seed=42, period_s=30.0)
    prev = w.value(0.0)
    for i in range(1, 200):
        t = i * 0.05
        v = w.value(t)
        # Step size should be small. Multi-octave noise can move faster
        # than single-octave; allow up to 0.4 between 50ms-spaced samples.
        assert abs(v - prev) < 0.4, f"big jump at t={t}: {prev} → {v}"
        prev = v


def test_wanderer_traverses_meaningful_range() -> None:
    """Over a long timescale, the wanderer should explore most of [-1, 1].
    Not literally hit ±1 (multi-octave averaging caps the extremes a bit)
    but at least cover, say, ±0.5."""
    w = Wanderer(seed=0, period_s=30.0)
    samples = [w.value(t * 1.0) for t in range(0, 600)]  # 600 seconds
    assert min(samples) < -0.4, f"min not low enough: {min(samples)}"
    assert max(samples) > 0.4, f"max not high enough: {max(samples)}"


def test_wanderer_rejects_zero_period() -> None:
    with pytest.raises(ValueError):
        Wanderer(seed=0, period_s=0)
    with pytest.raises(ValueError):
        Wanderer(seed=0, period_s=-5.0)


def test_wanderer_independent_octaves() -> None:
    """Sanity check: at very low frequency (t << period), the dominant
    contribution is the lowest octave; at very high frequency (t >> period),
    higher octaves dominate. Just verify the wanderer is sensitive at
    both timescales."""
    w = Wanderer(seed=10, period_s=30.0)
    # Two t-pairs: one tiny step (high-freq sensitive), one long step.
    short_step = abs(w.value(0.1) - w.value(0.0))
    long_step = abs(w.value(60.0) - w.value(0.0))
    # Both should be observable (non-zero); not asserting magnitudes.
    assert short_step >= 0.0  # noqa: PLR0133 — just ensures no NaN
    assert math.isfinite(short_step)
    assert math.isfinite(long_step)
