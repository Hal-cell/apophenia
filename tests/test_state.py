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
