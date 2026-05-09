"""Smoke tests for the VisualState pydantic schema (post-autopilot)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apophenia.state import (
    N_CHANNELS,
    FxState,
    PaletteState,
    VisualState,
)


def test_default_state_constructs() -> None:
    s = VisualState()
    assert len(s.channel_weight) == N_CHANNELS
    assert s.transport.freeze is False
    assert s.palette.saturation == 1.0
    assert s.fx.kaleidoscope == 1
    assert s.fx.bloom == 0.3


def test_palette_clamps_via_validation() -> None:
    with pytest.raises(ValidationError):
        PaletteState(hue=1.5)
    with pytest.raises(ValidationError):
        PaletteState(saturation=3.0)


def test_fx_clamps_via_validation() -> None:
    with pytest.raises(ValidationError):
        FxState(glitch=1.5)
    with pytest.raises(ValidationError):
        FxState(kaleidoscope=0)
    with pytest.raises(ValidationError):
        FxState(kaleidoscope=99)
    with pytest.raises(ValidationError):
        FxState(bloom=-0.1)


def test_channel_weight_wrong_length_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualState(channel_weight=[1.0, 1.0, 1.0])
