"""Smoke tests for the VisualState pydantic schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apophenia.state import N_CHANNELS, BlendState, VisualState


def test_default_state_constructs() -> None:
    s = VisualState()
    assert s.text.prompt
    assert len(s.channel_weight) == N_CHANNELS
    assert s.cfg == 5.0
    assert s.transport.freeze is False


def test_blend_clamps_via_validation() -> None:
    with pytest.raises(ValidationError):
        BlendState(audio_text=1.5)
    with pytest.raises(ValidationError):
        BlendState(shader_ai=-0.1)


def test_channel_weight_wrong_length_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualState(channel_weight=[1.0, 1.0, 1.0])
