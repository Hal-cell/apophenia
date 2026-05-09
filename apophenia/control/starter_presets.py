"""Curated 12-preset starter bank shipped with the package.

Phase 10 rewrite: each preset is a snapshot of the slim post-AI-strip
`VisualState` — palette + post-FX + channel-weight distribution + mood.
No text prompts, no AI blend params; everything here directly steers
the GLSL shader engine and Compositor.

The 12 starters are laid out as 4 axes × 3 presets each across slots 1-12:

  Slots 1–3   → tonal palette (warm / cool / neutral)
  Slots 4–6   → energy distribution across 14 channels
  Slots 7–9   → kaleidoscope geometry (3-fold / 6-fold / 9-fold)
  Slots 10–12 → post-FX intensity (subtle / lens / rupture)

Slots 13–16 ship empty so the user has space to save their own
without first deleting an existing one.
"""

from __future__ import annotations

from typing import Any

STARTER_DATA: list[tuple[str, dict[str, Any]]] = [
    # ---- 1–3: tonal palette ---- #
    ("warm",    {"palette": {"hue": 0.05, "saturation": 1.1}}),
    ("cool",    {"palette": {"hue": 0.55, "saturation": 0.95}}),
    ("neutral", {"palette": {"hue": 0.0,  "saturation": 0.7}}),
    # ---- 4–6: energy distribution ---- #
    ("front_heavy", {
        # ch1-4 full, ch5-14 fades — feature percussive / lead channels.
        "channel_weight": [
            1.0, 1.0, 1.0, 1.0,
            0.7, 0.6, 0.5, 0.4,
            0.3, 0.3, 0.2, 0.2,
            0.1, 0.1,
        ],
    }),
    ("back_heavy", {
        # ch1-4 quiet, ch9-14 dominant — feature pads / drones / FX.
        "channel_weight": [
            0.2, 0.3, 0.3, 0.4,
            0.5, 0.6, 0.7, 0.8,
            1.0, 1.0, 1.0, 1.0,
            1.0, 1.0,
        ],
    }),
    ("spread", {
        # alternating low / high so adjacent layers never both fire —
        # gives a wider visual texture instead of clumped intensity.
        "channel_weight": [
            1.0, 0.4, 1.0, 0.4,
            1.0, 0.4, 1.0, 0.4,
            1.0, 0.4, 1.0, 0.4,
            1.0, 0.4,
        ],
    }),
    # ---- 7–9: kaleidoscope geometry ---- #
    ("tri",   {"fx": {"kaleidoscope": 3}, "palette": {"saturation": 1.1}}),
    ("hex",   {"fx": {"kaleidoscope": 6}, "palette": {"saturation": 1.15}}),
    ("ennea", {"fx": {"kaleidoscope": 9}, "palette": {"saturation": 1.25}}),
    # ---- 10–12: post-FX intensity ---- #
    ("subtle", {"fx": {"glitch": 0.05, "chromatic": 0.1}}),
    ("lens",   {
        "fx": {"glitch": 0.0, "chromatic": 0.6},
        "palette": {"saturation": 1.2},
    }),
    ("rupture", {
        "fx": {"glitch": 0.7, "chromatic": 0.4, "kaleidoscope": 4},
        "palette": {"saturation": 1.3},
    }),
]


def starter_presets_dict() -> dict[str, Any]:
    """Build a `PresetBank.model_dump()`-shaped dict from `STARTER_DATA`.

    Done lazily (and at this dict shape) so we don't need to import
    `VisualState` until the bank is actually materialised — keeps cold
    import time low, and avoids circular-import hazards.
    """
    from apophenia.control.presets import (
        PRESET_BANK_SIZE,
        PRESET_FORMAT_VERSION,
    )
    from apophenia.state import VisualState

    presets: list[dict[str, Any]] = []
    for label, partial in STARTER_DATA:
        # Validate-then-dump round-trip to fill in defaults from the schema.
        # Schema drift fails loudly here at import time rather than silently
        # shipping a broken starter.
        state = VisualState.model_validate(partial)
        presets.append({"label": label, "state": state.model_dump()})
    while len(presets) < PRESET_BANK_SIZE:
        presets.append({"label": "", "state": None})
    return {"version": PRESET_FORMAT_VERSION, "presets": presets}
