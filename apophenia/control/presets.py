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


def load(path: Path | None = None, use_starter: bool = True) -> PresetBank:
    """Read the preset bank from disk.

    On missing file we materialise the curated 12-slot starter bank
    (see `starter_presets.STARTER_DATA`) and persist it so the next
    launch reads the user's own (now-editable) file. Pass
    `use_starter=False` for tests that want a clean empty bank without
    spilling starter content into a temp dir.

    On corrupt files or version mismatch we *also* fall back to the
    starter — giving up the user's broken file is better than crashing
    on every launch, and using the starters at this fork point keeps
    first-run and recovery experiences consistent.
    """
    p = path or default_path()
    if not p.exists():
        if use_starter:
            bank = _starter_bank()
            try:
                save(bank, p)
            except OSError:
                # Read-only fs / permissions → just return in-memory bank.
                pass
            return bank
        return PresetBank()
    try:
        bank = PresetBank.model_validate_json(p.read_text())
    except Exception:  # noqa: BLE001 — corrupt file → starter / empty
        return _starter_bank() if use_starter else PresetBank()
    if bank.version != PRESET_FORMAT_VERSION:
        return _starter_bank() if use_starter else PresetBank()
    return bank


def _starter_bank() -> PresetBank:
    """Build a `PresetBank` from `starter_presets.STARTER_DATA`."""
    # Lazy import keeps `presets` cold import light + avoids circular
    # imports with `apophenia.state`.
    from apophenia.control.starter_presets import starter_presets_dict

    return PresetBank.model_validate(starter_presets_dict())


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
