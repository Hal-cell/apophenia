"""16-slot preset bank persisted to `~/.config/apophenia/presets.json`.

A preset captures a full `VisualState` snapshot plus a user-supplied
label. Empty slots are represented by `state=None`. Save/recall is
keyed by integer index; the order is the order they appear in the UI.

V1 keeps it simple: synchronous file I/O on every save, no migration
machinery. If the on-disk format changes we bump `version` and refuse
to load older formats.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from apophenia.state import VisualState

PRESET_BANK_SIZE = 16
PRESET_FORMAT_VERSION = 1


class Preset(BaseModel):
    """One preset slot. `state=None` means empty."""

    label: str = ""
    state: VisualState | None = None


class PresetBank(BaseModel):
    """Container for the 16 slots plus a format version field for
    forward compatibility."""

    version: int = PRESET_FORMAT_VERSION
    presets: list[Preset] = Field(
        default_factory=lambda: [Preset() for _ in range(PRESET_BANK_SIZE)]
    )

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        """Normalise to exactly 16 slots — pad or truncate as needed."""
        if len(self.presets) < PRESET_BANK_SIZE:
            self.presets = list(self.presets) + [
                Preset() for _ in range(PRESET_BANK_SIZE - len(self.presets))
            ]
        elif len(self.presets) > PRESET_BANK_SIZE:
            self.presets = self.presets[:PRESET_BANK_SIZE]


def default_path() -> Path:
    """`~/.config/apophenia/presets.json`. XDG-style on macOS / Linux."""
    return Path.home() / ".config" / "apophenia" / "presets.json"


def load(path: Path | None = None) -> PresetBank:
    """Read the preset bank from disk; return a fresh empty bank if
    the file doesn't exist yet, or if it's from an incompatible
    `version` (rather than crash, we let users start over).
    """
    p = path or default_path()
    if not p.exists():
        return PresetBank()
    try:
        bank = PresetBank.model_validate_json(p.read_text())
    except Exception:  # noqa: BLE001 — corrupt file → silently restart
        return PresetBank()
    if bank.version != PRESET_FORMAT_VERSION:
        return PresetBank()
    return bank


def save(bank: PresetBank, path: Path | None = None) -> None:
    """Write the bank to disk, creating the parent directory if needed."""
    p = path or default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bank.model_dump_json(indent=2))


def save_slot(
    bank: PresetBank,
    idx: int,
    state: VisualState,
    label: str | None = None,
) -> PresetBank:
    """Return a copy of `bank` with slot `idx` overwritten.

    Pure-functional — caller decides whether to persist via `save()`.
    Default label is "preset {idx+1}" if the user didn't provide one.
    """
    if idx < 0 or idx >= PRESET_BANK_SIZE:
        raise IndexError(f"preset index {idx} out of range [0, {PRESET_BANK_SIZE})")
    new_presets = list(bank.presets)
    new_presets[idx] = Preset(
        label=label or f"preset {idx + 1}",
        state=state,
    )
    return bank.model_copy(update={"presets": new_presets})


def clear_slot(bank: PresetBank, idx: int) -> PresetBank:
    if idx < 0 or idx >= PRESET_BANK_SIZE:
        raise IndexError(f"preset index {idx} out of range [0, {PRESET_BANK_SIZE})")
    new_presets = list(bank.presets)
    new_presets[idx] = Preset()
    return bank.model_copy(update={"presets": new_presets})
