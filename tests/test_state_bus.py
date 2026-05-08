"""Tests for the StateBus mailbox + deep-merge update semantics."""

from __future__ import annotations

import threading

import pytest
from pydantic import ValidationError

from apophenia.control.state_bus import StateBus, _deep_merge
from apophenia.state import VisualState

# --------------------------------------------------------------------------- #
# _deep_merge primitives
# --------------------------------------------------------------------------- #


def test_deep_merge_replaces_scalars() -> None:
    base = {"a": 1, "b": 2}
    out = _deep_merge(base, {"a": 99})
    assert out == {"a": 99, "b": 2}
    # Source unchanged
    assert base == {"a": 1, "b": 2}


def test_deep_merge_recurses_dicts() -> None:
    base = {"x": {"a": 1, "b": 2}, "y": 3}
    out = _deep_merge(base, {"x": {"a": 99}})
    assert out == {"x": {"a": 99, "b": 2}, "y": 3}


def test_deep_merge_replaces_lists_wholesale() -> None:
    """Lists are scalars in the merge; UI sends the whole list when
    one channel weight changes."""
    base = {"channel_weight": [1.0, 1.0, 1.0]}
    out = _deep_merge(base, {"channel_weight": [0.5, 0.0, 1.0]})
    assert out == {"channel_weight": [0.5, 0.0, 1.0]}


def test_deep_merge_dict_overrides_non_dict_in_base() -> None:
    base = {"k": "scalar"}
    out = _deep_merge(base, {"k": {"a": 1}})
    assert out == {"k": {"a": 1}}


# --------------------------------------------------------------------------- #
# StateBus
# --------------------------------------------------------------------------- #


def test_state_bus_starts_with_default_state() -> None:
    bus = StateBus()
    s = bus.get()
    assert isinstance(s, VisualState)
    # Defaults from the schema.
    assert s.blend.audio_text == 0.5
    assert s.transport.freeze is False
    assert s.channel_weight == [1.0] * 14


def test_state_bus_get_returns_defensive_copy() -> None:
    """Mutating the returned state must not affect the bus."""
    bus = StateBus()
    s1 = bus.get()
    s1.blend.audio_text = 0.9  # mutate copy
    s2 = bus.get()
    assert s2.blend.audio_text == 0.5


def test_state_bus_update_partial_blend() -> None:
    bus = StateBus()
    new_state = bus.update({"blend": {"audio_text": 0.7}})
    assert new_state.blend.audio_text == 0.7
    # Other top-level fields untouched.
    assert new_state.motion.speed == 1.0
    assert new_state.palette.saturation == 1.0


def test_state_bus_update_partial_motion() -> None:
    bus = StateBus()
    new_state = bus.update({"motion": {"speed": 1.5, "density": 0.8}})
    assert new_state.motion.speed == 1.5
    assert new_state.motion.density == 0.8
    # Other motion field untouched.
    assert new_state.motion.onset_sensitivity == 1.0


def test_state_bus_update_channel_weight_full_array() -> None:
    bus = StateBus()
    weights = [0.0, 0.5, 1.0, 0.5, 0.0, 0.5, 1.0, 0.5, 0.0, 0.5, 1.0, 0.5, 0.0, 0.5]
    new_state = bus.update({"channel_weight": weights})
    assert new_state.channel_weight == weights


def test_state_bus_update_rejects_invalid_range() -> None:
    """Pydantic Field constraints catch out-of-range values."""
    bus = StateBus()
    with pytest.raises(ValidationError):
        bus.update({"blend": {"audio_text": 1.5}})  # max is 1.0


def test_state_bus_update_rejects_wrong_channel_count() -> None:
    bus = StateBus()
    with pytest.raises((ValidationError, ValueError)):
        bus.update({"channel_weight": [1.0, 1.0, 1.0]})  # not 14


def test_state_bus_replace_swaps_entire_state() -> None:
    bus = StateBus()
    new = VisualState()
    new.motion.speed = 1.7
    new.blend.audio_text = 0.1
    out = bus.replace(new)
    assert out.motion.speed == 1.7
    assert out.blend.audio_text == 0.1
    # Subsequent get() reflects it.
    assert bus.get().motion.speed == 1.7


def test_state_bus_thread_safety() -> None:
    """Many threads patching simultaneously shouldn't crash or tear."""
    bus = StateBus()
    stop = threading.Event()
    errors: list[Exception] = []

    def writer(field: str) -> None:
        try:
            for i in range(200):
                if stop.is_set():
                    return
                bus.update({"blend": {field: (i % 100) / 100.0}})
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def reader() -> None:
        try:
            for _ in range(200):
                if stop.is_set():
                    return
                _ = bus.get()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    # Three concurrent writers — one to blend, two to motion. Different
    # subtrees stress the deep-merge under contention.
    def writer_motion(field: str) -> None:
        try:
            for i in range(200):
                if stop.is_set():
                    return
                bus.update({"motion": {field: (i % 100) / 100.0}})
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ws = [
        threading.Thread(target=writer, args=("audio_text",), daemon=True),
        threading.Thread(target=writer_motion, args=("speed",), daemon=True),
        threading.Thread(target=writer_motion, args=("density",), daemon=True),
    ]
    rs = [threading.Thread(target=reader, daemon=True) for _ in range(3)]
    for t in ws + rs:
        t.start()
    for t in ws + rs:
        t.join(timeout=2.0)
    stop.set()
    assert not errors, f"thread errors: {errors}"


def test_state_bus_update_text_prompt() -> None:
    bus = StateBus()
    new = bus.update({"text": {"prompt": "molten glass cathedral"}})
    assert new.text.prompt == "molten glass cathedral"


def test_state_bus_update_nested_then_top_level() -> None:
    """Two consecutive partial updates compose correctly."""
    bus = StateBus()
    bus.update({"blend": {"audio_text": 0.7}})
    s = bus.update({"motion": {"speed": 1.5}})
    assert s.blend.audio_text == 0.7  # carried over
    assert s.motion.speed == 1.5
