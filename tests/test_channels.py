"""Tests for ChannelMap + ChannelRole + CLI range parsing."""

from __future__ import annotations

import pytest

from synapse.channels import ChannelMap, ChannelRole, _parse_range_spec

# --------------------------------------------------------------------------- #
# Range parser
# --------------------------------------------------------------------------- #


def test_parse_single_int() -> None:
    assert list(_parse_range_spec("3")) == [3]


def test_parse_comma_list() -> None:
    assert list(_parse_range_spec("1,3,5")) == [1, 3, 5]


def test_parse_range_inclusive() -> None:
    assert list(_parse_range_spec("3-7")) == [3, 4, 5, 6, 7]


def test_parse_mixed() -> None:
    assert list(_parse_range_spec("1,3-5,9")) == [1, 3, 4, 5, 9]


def test_parse_whitespace_tolerant() -> None:
    assert list(_parse_range_spec(" 1 , 3 - 5 , 9 ")) == [1, 3, 4, 5, 9]


def test_parse_empty() -> None:
    assert list(_parse_range_spec("")) == []
    assert list(_parse_range_spec("   ")) == []


def test_parse_rejects_bad_int() -> None:
    with pytest.raises(ValueError):
        list(_parse_range_spec("foo"))


def test_parse_rejects_inverted_range() -> None:
    with pytest.raises(ValueError):
        list(_parse_range_spec("5-2"))


# --------------------------------------------------------------------------- #
# ChannelMap
# --------------------------------------------------------------------------- #


def test_default_all_audio() -> None:
    cm = ChannelMap.from_cli(n_channels=14)
    for i in range(14):
        assert cm.role(i) == ChannelRole.AUDIO


def test_role_assignment() -> None:
    cm = ChannelMap.from_cli(n_channels=14, gate="1,2", cv="3-5")
    assert cm.role(0) == ChannelRole.GATE
    assert cm.role(1) == ChannelRole.GATE
    assert cm.role(2) == ChannelRole.CV
    assert cm.role(3) == ChannelRole.CV
    assert cm.role(4) == ChannelRole.CV
    # Unassigned → AUDIO.
    assert cm.role(5) == ChannelRole.AUDIO
    assert cm.role(13) == ChannelRole.AUDIO


def test_channels_with_returns_zero_indexed() -> None:
    """CLI is 1-based for performer ergonomics; internal indices are 0-based.
    Verify the conversion is correct."""
    cm = ChannelMap.from_cli(n_channels=14, gate="1,5,14")
    assert cm.channels_with(ChannelRole.GATE) == [0, 4, 13]


def test_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="out of range"):
        ChannelMap.from_cli(n_channels=14, gate="15")
    with pytest.raises(ValueError, match="out of range"):
        ChannelMap.from_cli(n_channels=14, cv="0")  # 1-based; 0 is invalid


def test_rejects_double_assignment() -> None:
    with pytest.raises(ValueError, match="assigned both"):
        ChannelMap.from_cli(n_channels=14, gate="3", cv="3")


def test_rejects_zero_channels() -> None:
    with pytest.raises(ValueError):
        ChannelMap.from_cli(n_channels=0)


def test_to_dict() -> None:
    cm = ChannelMap.from_cli(n_channels=8, gate="1", cv="2-3")
    d = cm.to_dict()
    assert d == {
        "audio": [3, 4, 5, 6, 7],   # zero-indexed
        "cv": [1, 2],
        "gate": [0],
    }
