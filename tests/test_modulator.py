"""Tests for the autopilot Modulator — wanderers + audio → VisualState."""

from __future__ import annotations

import pytest

from apophenia.audio.features_fast import FastFeatures
from apophenia.autopilot import Modulator
from apophenia.state import N_CHANNELS, VisualState


def test_modulator_returns_visual_state() -> None:
    m = Modulator(seed=1)
    s = m.state(0.0)
    assert isinstance(s, VisualState)


def test_modulator_state_passes_schema() -> None:
    """All produced states pass Pydantic validation — i.e. all wanderer-
    derived values land in their declared ranges."""
    m = Modulator(seed=42)
    # Sample over a wide range of times; modulator uses its own clamps
    # so out-of-range values would only escape via a clamp bug.
    for t in [0.0, 1.0, 13.7, 60.0, 300.0, 1800.0, 7200.0]:
        s = m.state(t)
        # Pydantic would have raised on construction if any field was
        # out of range.
        assert 0.0 <= s.palette.hue <= 1.0
        assert 0.0 <= s.palette.saturation <= 2.0
        assert 0.0 <= s.fx.bloom <= 1.0
        assert 0.0 <= s.fx.glitch <= 1.0
        assert 0.0 <= s.fx.chromatic <= 1.0
        assert 1 <= s.fx.kaleidoscope <= 12
        assert len(s.channel_weight) == N_CHANNELS
        assert all(0.0 <= w <= 1.0 for w in s.channel_weight)


def test_modulator_deterministic_for_same_seed() -> None:
    """Same seed + same time + same features → byte-identical state."""
    m1 = Modulator(seed=7)
    m2 = Modulator(seed=7)
    s1 = m1.state(13.5)
    s2 = m2.state(13.5)
    assert s1.model_dump() == s2.model_dump()


def test_modulator_different_seeds_decorrelate() -> None:
    """Two modulators with different seeds should produce different
    states at the same time."""
    m1 = Modulator(seed=1)
    m2 = Modulator(seed=2)
    diffs = 0
    for t in [0.0, 5.0, 30.0, 120.0]:
        s1 = m1.state(t)
        s2 = m2.state(t)
        if abs(s1.palette.hue - s2.palette.hue) > 0.01:
            diffs += 1
        if abs(s1.fx.bloom - s2.fx.bloom) > 0.01:
            diffs += 1
    assert diffs >= 3


def test_modulator_state_evolves_over_time() -> None:
    """Sampling at distant t values should give different states —
    confirming it's actually animating, not stuck."""
    m = Modulator(seed=99)
    s_a = m.state(0.0)
    s_b = m.state(60.0)  # one minute later
    s_c = m.state(180.0)  # three minutes later
    # Hue (slowest wanderer) might still be similar at 60s but should
    # differ noticeably at 180s. Bloom (45s period) should differ at 60s.
    diffs = (
        abs(s_a.palette.hue - s_c.palette.hue)
        + abs(s_a.fx.bloom - s_b.fx.bloom)
        + abs(s_a.palette.saturation - s_c.palette.saturation)
    )
    assert diffs > 0.05


def test_modulator_audio_couples_to_saturation() -> None:
    """Loud audio should boost saturation vs. silent audio at the same t."""
    m = Modulator(seed=0)
    silent = FastFeatures(rms=[0.0] * 14, n_channels=14)
    loud = FastFeatures(rms=[0.9] * 14, n_channels=14)
    s_silent = m.state(10.0, silent)
    s_loud = m.state(10.0, loud)
    # Loud should have higher saturation (rms_avg adds 0.5 × rms).
    assert s_loud.palette.saturation > s_silent.palette.saturation


def test_modulator_audio_couples_to_glitch() -> None:
    """Big onsets push glitch above zero; quiet onsets keep it at zero."""
    m = Modulator(seed=0)
    quiet = FastFeatures(onset_envelope=[0.1] * 14, n_channels=14)
    big_hit = FastFeatures(onset_envelope=[0.9] * 14, n_channels=14)
    s_quiet = m.state(5.0, quiet)
    s_hit = m.state(5.0, big_hit)
    assert s_quiet.fx.glitch == 0.0
    assert s_hit.fx.glitch > 0.0


def test_modulator_handles_no_features() -> None:
    """Cold-boot path: features=None should still produce a valid state."""
    m = Modulator(seed=0)
    s = m.state(0.0, None)
    assert isinstance(s, VisualState)
    # No audio → glitch must be zero (driven only by onset_max)
    assert s.fx.glitch == 0.0


def test_modulator_handles_empty_features() -> None:
    """Defensive: features with empty rms / onset arrays don't crash."""
    m = Modulator(seed=0)
    feats = FastFeatures(rms=[], peak=[], centroid=[], onset_envelope=[])
    s = m.state(0.0, feats)
    assert isinstance(s, VisualState)


def test_modulator_freeze_is_rare() -> None:
    """Sample many time points; the freeze flag should be True for less
    than ~25% of them. (180s wanderer × 4 octaves crossing > 0.85
    happens infrequently.)"""
    m = Modulator(seed=0)
    n = 1000
    freezes = sum(1 for i in range(n) if m.state(i * 1.0).transport.freeze)
    fraction = freezes / n
    assert fraction < 0.25, f"freeze fired {fraction:.1%} of samples — too often"


def test_modulator_kaleidoscope_takes_discrete_values() -> None:
    """Kaleidoscope should only ever be one of the discrete {1, 3, 6, 9}
    values produced by the modulator."""
    m = Modulator(seed=42)
    seen = {m.state(t * 0.5).fx.kaleidoscope for t in range(2000)}
    assert seen.issubset({1, 3, 6, 9})


def test_modulator_channel_weights_floor() -> None:
    """The Gaussian-spotlight weights should never go below 0.15 (the
    floor enforced in the modulator)."""
    m = Modulator(seed=1)
    for t in [0.0, 7.5, 33.0, 90.0]:
        s = m.state(t)
        for w in s.channel_weight:
            assert w >= 0.15 - 1e-9, f"weight too low at t={t}: {w}"


def test_modulator_tick_count_increments() -> None:
    """tick_count is exposed for telemetry — should increment monotonically."""
    m = Modulator(seed=0)
    assert m.tick_count == 0
    m.state(0.0)
    assert m.tick_count == 1
    for _ in range(10):
        m.state(0.0)
    assert m.tick_count == 11


@pytest.mark.parametrize("seed", [0, 1, 42, 9999])
def test_modulator_no_nans_or_infs(seed: int) -> None:
    """Long sweep, multiple seeds — never produces NaN / inf in any field."""
    import math as _math

    m = Modulator(seed=seed)
    for t in range(0, 3600, 7):
        s = m.state(t * 1.0)
        assert _math.isfinite(s.palette.hue)
        assert _math.isfinite(s.palette.saturation)
        assert _math.isfinite(s.fx.bloom)
        assert _math.isfinite(s.fx.glitch)
        assert _math.isfinite(s.fx.chromatic)
        for w in s.channel_weight:
            assert _math.isfinite(w)
