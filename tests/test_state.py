"""Smoke tests for the VisualState pydantic schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apophenia.state import N_CHANNELS, BlendState, MotionState, VisualState


def test_default_state_constructs() -> None:
    s = VisualState()
    assert s.text.prompt
    assert len(s.channel_weight) == N_CHANNELS
    assert s.transport.freeze is False
    # Phase-10 defaults: motion is at neutral, mood is centred.
    assert s.motion.speed == 1.0
    assert s.motion.density == 0.5
    assert s.motion.onset_sensitivity == 1.0
    assert s.mood.valence == 0.0
    assert s.mood.arousal == 0.0


def test_blend_clamps_via_validation() -> None:
    with pytest.raises(ValidationError):
        BlendState(audio_text=1.5)
    with pytest.raises(ValidationError):
        BlendState(audio_text=-0.1)


def test_motion_clamps_via_validation() -> None:
    with pytest.raises(ValidationError):
        MotionState(speed=2.5)  # max 2.0
    with pytest.raises(ValidationError):
        MotionState(density=1.5)  # max 1.0
    with pytest.raises(ValidationError):
        MotionState(onset_sensitivity=-0.1)  # min 0.0


def test_channel_weight_wrong_length_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualState(channel_weight=[1.0, 1.0, 1.0])


def test_fx_trail_default_zero_and_valid_range() -> None:
    """Phase-11 FxState.trail: defaults to 0, valid in [0, 0.99]. Capped
    below 1.0 to prevent runaway feedback loops."""
    s = VisualState()
    assert s.fx.trail == 0.0
    # Boundary values should validate.
    s_lo = VisualState()
    s_lo.fx.trail = 0.0
    s_hi = VisualState()
    s_hi.fx.trail = 0.99


def test_fx_trail_one_or_above_rejected() -> None:
    """trail=1 would mean the previous frame survives forever — pydantic
    refuses anything ≥ 0.99 + epsilon."""
    from apophenia.state import FxState

    with pytest.raises(ValidationError):
        FxState(trail=1.0)
    with pytest.raises(ValidationError):
        FxState(trail=1.5)
    with pytest.raises(ValidationError):
        FxState(trail=-0.1)


def test_force_state_defaults_and_ranges() -> None:
    """Phase-14 ForceState: TD-cluster-friendly defaults, all four
    levers validate at boundaries."""
    from apophenia.state import ForceState

    f = ForceState()
    assert f.noise == 0.5
    assert f.vortex == 0.4
    assert f.cohesion == 0.5
    assert f.max_speed == 2.0

    with pytest.raises(ValidationError):
        ForceState(noise=1.5)
    with pytest.raises(ValidationError):
        ForceState(vortex=-0.1)
    with pytest.raises(ValidationError):
        ForceState(cohesion=2.0)
    with pytest.raises(ValidationError):
        ForceState(max_speed=0.1)  # below 0.5 floor
    with pytest.raises(ValidationError):
        ForceState(max_speed=10.0)  # above 8.0 ceiling


def test_visual_state_includes_force_default() -> None:
    s = VisualState()
    assert s.force.cohesion == 0.5
    assert s.force.max_speed == 2.0


def test_force_streak_length_validates() -> None:
    """Phase-16: streak_length is the velocity-aligned line length in
    seconds-of-motion. Default 0.06 (subtle); range [0, 0.5]."""
    from apophenia.state import ForceState

    f = ForceState()
    assert f.streak_length == 0.06

    with pytest.raises(ValidationError):
        ForceState(streak_length=-0.1)
    with pytest.raises(ValidationError):
        ForceState(streak_length=0.6)  # above 0.5 ceiling
    # Boundary values should validate.
    f_zero = ForceState(streak_length=0.0)
    assert f_zero.streak_length == 0.0
    f_max = ForceState(streak_length=0.5)
    assert f_max.streak_length == 0.5
