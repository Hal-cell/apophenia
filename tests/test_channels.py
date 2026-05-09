"""Tests for ChannelMap + ChannelRole + CLI range parsing + live controller."""

from __future__ import annotations

import threading

import pytest

from synapse.channels import (
    ChannelMap,
    ChannelRole,
    ChannelRolesController,
    _parse_range_spec,
)

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


# --------------------------------------------------------------------------- #
# ChannelRolesController (live mutable state)
# --------------------------------------------------------------------------- #


def _ctrl(initial: list[str] | None = None) -> ChannelRolesController:
    """Build a controller from a list of role strings (e.g. ['audio','cv'])."""
    if initial is None:
        initial = ["audio"] * 4
    return ChannelRolesController([ChannelRole(r) for r in initial])


def test_controller_starts_with_initial_roles() -> None:
    c = _ctrl(["audio", "cv", "gate", "audio"])
    assert [r.value for r in c.get()] == ["audio", "cv", "gate", "audio"]
    assert c.role(1) == ChannelRole.CV
    assert c.n_channels == 4
    assert c.version() == 0


def test_controller_set_one_updates_role_and_bumps_version() -> None:
    c = _ctrl(["audio"] * 4)
    c.set_one(2, "cv")
    assert c.role(2) == ChannelRole.CV
    assert [r.value for r in c.get()] == ["audio", "audio", "cv", "audio"]
    assert c.version() == 1
    c.set_one(0, ChannelRole.GATE)  # accepts enum directly
    assert c.role(0) == ChannelRole.GATE
    assert c.version() == 2


def test_controller_set_one_rejects_bad_index() -> None:
    c = _ctrl(["audio"] * 4)
    with pytest.raises(ValueError, match="out of range"):
        c.set_one(4, "cv")
    with pytest.raises(ValueError, match="out of range"):
        c.set_one(-1, "cv")


def test_controller_set_one_rejects_bad_role() -> None:
    c = _ctrl(["audio"] * 4)
    with pytest.raises(ValueError, match="unknown role"):
        c.set_one(0, "trigger")
    with pytest.raises(ValueError, match="unknown role"):
        c.set_one(0, "AUDIO_AND_CV")


def test_controller_set_one_accepts_uppercase_strings() -> None:
    c = _ctrl(["audio"] * 4)
    c.set_one(0, "CV")
    assert c.role(0) == ChannelRole.CV


def test_controller_set_all_replaces_full_list() -> None:
    c = _ctrl(["audio"] * 4)
    c.set_all(["gate", "gate", "cv", "cv"])
    assert [r.value for r in c.get()] == ["gate", "gate", "cv", "cv"]
    assert c.version() == 1


def test_controller_set_all_rejects_length_mismatch() -> None:
    c = _ctrl(["audio"] * 4)
    with pytest.raises(ValueError, match="expected 4 roles"):
        c.set_all(["audio", "cv"])
    with pytest.raises(ValueError, match="expected 4 roles"):
        c.set_all(["audio"] * 5)


def test_controller_get_returns_independent_snapshot() -> None:
    """Mutating the snapshot mustn't mutate the controller's state."""
    c = _ctrl(["audio", "cv", "gate", "audio"])
    snap = c.get()
    snap[0] = ChannelRole.GATE  # mutate snapshot
    # Controller state unchanged.
    assert c.role(0) == ChannelRole.AUDIO


def test_controller_channels_with_role() -> None:
    c = _ctrl(["audio", "gate", "cv", "gate", "audio"])
    assert c.channels_with(ChannelRole.GATE) == [1, 3]
    assert c.channels_with(ChannelRole.CV) == [2]
    assert c.channels_with(ChannelRole.AUDIO) == [0, 4]


def test_controller_snapshot_returns_channelmap() -> None:
    c = _ctrl(["audio", "cv", "gate", "audio"])
    cm = c.snapshot()
    assert isinstance(cm, ChannelMap)
    assert cm.role(1) == ChannelRole.CV
    # Snapshot detached: subsequent mutations don't affect it.
    c.set_one(1, "audio")
    assert cm.role(1) == ChannelRole.CV  # snapshot unchanged
    assert c.role(1) == ChannelRole.AUDIO  # controller did change


def test_controller_thread_safe_under_contention() -> None:
    """Concurrent set_one calls + reads should never crash or yield
    invalid state. We can't easily assert on ordering, but we can
    assert the final state is one of the writers' last-applied roles
    and the version count matches the total writes."""
    c = _ctrl(["audio"] * 4)
    stop = threading.Event()
    write_counts = [0, 0]

    def writer(thread_idx: int, role_str: str) -> None:
        while not stop.is_set():
            c.set_one(thread_idx % 4, role_str)
            write_counts[thread_idx] += 1

    def reader() -> None:
        while not stop.is_set():
            roles = c.get()
            assert len(roles) == 4
            for r in roles:
                assert r in (ChannelRole.AUDIO, ChannelRole.CV, ChannelRole.GATE)

    threads = [
        threading.Thread(target=writer, args=(0, "cv"), daemon=True),
        threading.Thread(target=writer, args=(1, "gate"), daemon=True),
        threading.Thread(target=reader, daemon=True),
        threading.Thread(target=reader, daemon=True),
    ]
    for t in threads:
        t.start()
    threading.Event().wait(0.05)
    stop.set()
    for t in threads:
        t.join(timeout=1.0)

    # Every successful write bumps version exactly once.
    assert c.version() == sum(write_counts)
    # Final state should still be 4 channels with valid roles.
    assert len(c.get()) == 4
