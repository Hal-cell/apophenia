"""Tests for the 16-slot preset bank: schema, save/recall, persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from apophenia.control.presets import (
    PRESET_BANK_SIZE,
    PRESET_FORMAT_VERSION,
    Preset,
    PresetBank,
    clear_slot,
    load,
    save,
    save_slot,
)
from apophenia.state import VisualState

# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


def test_empty_preset_has_no_state() -> None:
    p = Preset()
    assert p.state is None
    assert p.label == ""


def test_preset_bank_defaults_to_16_empty_slots() -> None:
    bank = PresetBank()
    assert len(bank.presets) == PRESET_BANK_SIZE
    assert bank.version == PRESET_FORMAT_VERSION
    assert all(p.state is None for p in bank.presets)


def test_preset_bank_pads_short_input() -> None:
    """If someone hands us a 3-slot list, normalise to 16."""
    bank = PresetBank(presets=[Preset(label="a"), Preset(label="b"), Preset(label="c")])
    assert len(bank.presets) == PRESET_BANK_SIZE
    assert bank.presets[0].label == "a"
    assert bank.presets[1].label == "b"
    assert bank.presets[2].label == "c"
    for p in bank.presets[3:]:
        assert p.label == ""
        assert p.state is None


def test_preset_bank_truncates_long_input() -> None:
    bank = PresetBank(presets=[Preset(label=f"p{i}") for i in range(20)])
    assert len(bank.presets) == PRESET_BANK_SIZE
    assert bank.presets[-1].label == f"p{PRESET_BANK_SIZE - 1}"


# --------------------------------------------------------------------------- #
# save_slot / clear_slot
# --------------------------------------------------------------------------- #


def test_save_slot_writes_state_into_chosen_index() -> None:
    bank = PresetBank()
    state = VisualState()
    state.palette.hue = 0.7

    new_bank = save_slot(bank, 3, state, label="warm-violet")
    assert new_bank.presets[3].label == "warm-violet"
    assert new_bank.presets[3].state is not None
    assert new_bank.presets[3].state.palette.hue == 0.7
    for i, p in enumerate(new_bank.presets):
        if i != 3:
            assert p.state is None
    # Original bank unchanged (pure-functional).
    assert bank.presets[3].state is None


def test_save_slot_default_label() -> None:
    bank = PresetBank()
    new_bank = save_slot(bank, 5, VisualState())
    assert new_bank.presets[5].label == "preset 6"


def test_save_slot_rejects_out_of_range() -> None:
    bank = PresetBank()
    state = VisualState()
    with pytest.raises(IndexError):
        save_slot(bank, -1, state)
    with pytest.raises(IndexError):
        save_slot(bank, PRESET_BANK_SIZE, state)


def test_clear_slot_resets_to_empty() -> None:
    bank = PresetBank()
    bank = save_slot(bank, 7, VisualState(), label="x")
    assert bank.presets[7].state is not None
    bank = clear_slot(bank, 7)
    assert bank.presets[7].state is None
    assert bank.presets[7].label == ""


def test_clear_slot_rejects_out_of_range() -> None:
    bank = PresetBank()
    with pytest.raises(IndexError):
        clear_slot(bank, PRESET_BANK_SIZE + 5)


# --------------------------------------------------------------------------- #
# Persistence (load / save)
# --------------------------------------------------------------------------- #


def test_load_returns_empty_bank_when_file_missing_use_starter_false(
    tmp_path: Path,
) -> None:
    """`use_starter=False` keeps the original empty-on-missing semantics."""
    p = tmp_path / "none.json"
    bank = load(p, use_starter=False)
    assert isinstance(bank, PresetBank)
    assert all(slot.state is None for slot in bank.presets)


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "presets.json"
    bank = PresetBank()
    state = VisualState()
    state.palette.hue = 0.42
    state.fx.kaleidoscope = 6
    bank = save_slot(bank, 0, state, label="warm-hex")
    bank = save_slot(bank, 12, VisualState(), label="empty-but-saved")
    save(bank, p)
    assert p.exists()

    loaded = load(p)
    assert loaded.version == PRESET_FORMAT_VERSION
    assert loaded.presets[0].label == "warm-hex"
    assert loaded.presets[0].state is not None
    assert loaded.presets[0].state.palette.hue == 0.42
    assert loaded.presets[0].state.fx.kaleidoscope == 6
    assert loaded.presets[12].label == "empty-but-saved"


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    p = tmp_path / "a" / "b" / "c" / "presets.json"
    save(PresetBank(), p)
    assert p.exists()


def test_load_corrupt_file_returns_empty_bank(tmp_path: Path) -> None:
    """Garbage on disk shouldn't crash the app — silently start fresh."""
    p = tmp_path / "corrupt.json"
    p.write_text("{not valid json")
    bank = load(p, use_starter=False)
    assert isinstance(bank, PresetBank)
    assert all(slot.state is None for slot in bank.presets)


def test_load_old_version_returns_empty_bank(tmp_path: Path) -> None:
    """Forward-compat: future versions of apophenia bumping `version` will
    refuse to load the V1 file, rather than coerce mismatched fields."""
    p = tmp_path / "old.json"
    p.write_text('{"version": 999, "presets": []}')
    bank = load(p, use_starter=False)
    assert bank.version == PRESET_FORMAT_VERSION
    assert all(slot.state is None for slot in bank.presets)


# --------------------------------------------------------------------------- #
# Starter bank (Phase 8/10)
# --------------------------------------------------------------------------- #


def test_load_materialises_starter_bank_on_missing_file(tmp_path: Path) -> None:
    """First-launch experience: no preset file → load() returns the
    curated starter bank AND writes it to disk for the next launch."""
    p = tmp_path / "presets.json"
    assert not p.exists()
    bank = load(p)
    full = [pr for pr in bank.presets if pr.state is not None]
    empty = [pr for pr in bank.presets if pr.state is None]
    assert len(full) == 12
    assert len(empty) == 4
    assert all(pr.label.strip() for pr in full)
    assert p.exists()
    bank2 = load(p)
    assert [pr.label for pr in bank2.presets] == [pr.label for pr in bank.presets]


def test_load_does_not_override_existing_user_file(tmp_path: Path) -> None:
    """If the user has saved their own bank, starters must NOT clobber it."""
    p = tmp_path / "presets.json"
    user_bank = save_slot(PresetBank(), 0, VisualState(), label="my-thing")
    save(user_bank, p)

    loaded = load(p)
    assert loaded.presets[0].label == "my-thing"
    # Slot 1 in the starter bank would be "cool"; the user's file has
    # this slot empty, so the starter MUST NOT have leaked in.
    assert loaded.presets[1].state is None


def test_load_starter_includes_known_presets(tmp_path: Path) -> None:
    """Spot-check current starter labels."""
    p = tmp_path / "presets.json"
    bank = load(p)
    labels = {pr.label for pr in bank.presets if pr.state is not None}
    assert "warm" in labels
    assert "hex" in labels
    assert "rupture" in labels


def test_starter_bank_validates_against_schema() -> None:
    """If a starter ever drifts out of the VisualState schema, this fires
    before the bank ships."""
    from apophenia.control.starter_presets import starter_presets_dict

    bank_dict = starter_presets_dict()
    assert bank_dict["version"] == PRESET_FORMAT_VERSION
    assert len(bank_dict["presets"]) == PRESET_BANK_SIZE
