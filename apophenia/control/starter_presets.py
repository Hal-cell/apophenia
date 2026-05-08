"""Curated 12-preset starter bank shipped with the package.

Phase-10 retune: the V1 starter prompts described image content (e.g.
"molten glass cathedral, deep violet, ribbons of fire") which made
sense for SDXL-Turbo but is the wrong shape for V1.5's prompt →
shader-parameter architecture. Each starter now has a prompt composed
from PromptInterpreter vocabulary words — so a user clicking a slot
gets state that matches what the same prompt would produce if typed
directly.

Slots 1–4   start with "minimal / sparse" and ramp to "dense / loud".
Slots 5–8   organic → synthetic textures.
Slots 9–12  showcase the post-FX territory (kaleidoscope / glitch /
            chromatic).
Slots 13–16 ship empty so the user has space to save their own.

Each starter sets `text.prompt` plus a curated motion / palette / fx /
mood tuple. Save/load round-trips through the same `VisualState` schema
that powers the live state, so any schema drift fires an
import-time error rather than silently shipping a broken bank.
"""

from __future__ import annotations

from typing import Any

# Each entry is (label, partial state dict) deep-merged onto VisualState
# defaults at materialisation time.
STARTER_DATA: list[tuple[str, dict[str, Any]]] = [
    # ---- 1–4: minimal → loud (energy axis) ---- #
    (
        "bloom",
        {
            "text": {"prompt": "soft warm bloom"},
            "motion": {"speed": 0.7, "density": 0.6, "onset_sensitivity": 1.4},
            "palette": {"hue": 0.05, "saturation": 1.2},
            "mood": {"valence": 0.6, "arousal": -0.1},
        },
    ),
    (
        "paper",
        {
            "text": {"prompt": "subtle muted drift"},
            "motion": {"speed": 0.5, "density": 0.3, "onset_sensitivity": 0.6},
            "palette": {"hue": 0.08, "saturation": 0.55},
            "mood": {"valence": 0.2, "arousal": -0.4},
        },
    ),
    (
        "liquid_metal",
        {
            "text": {"prompt": "smooth cool flow"},
            "motion": {"speed": 0.8, "density": 0.55, "onset_sensitivity": 1.1},
            "palette": {"hue": 0.55, "saturation": 0.95},
            "fx": {"chromatic": 0.1},
            "mood": {"valence": -0.2, "arousal": 0.0},
        },
    ),
    (
        "cathedral",
        {
            "text": {"prompt": "violet agitated pulse"},
            "motion": {"speed": 1.4, "density": 0.7, "onset_sensitivity": 1.6},
            "palette": {"hue": 0.78, "saturation": 1.25},
            "fx": {"glitch": 0.05},
            "mood": {"valence": 0.4, "arousal": 0.6},
        },
    ),
    # ---- 5–8: organic → synthetic ---- #
    (
        "forest",
        {
            "text": {"prompt": "calm green drift"},
            "motion": {"speed": 0.5, "density": 0.45, "onset_sensitivity": 0.8},
            "palette": {"hue": 0.33, "saturation": 0.95},
            "fx": {"chromatic": 0.05},
            "mood": {"valence": 0.1, "arousal": -0.5},
        },
    ),
    (
        "coral",
        {
            "text": {"prompt": "warm cyan ripple"},
            "motion": {"speed": 0.8, "density": 0.55, "onset_sensitivity": 1.1},
            "palette": {"hue": 0.5, "saturation": 1.15},
            "fx": {"chromatic": 0.15},
            "mood": {"valence": 0.3, "arousal": 0.0},
        },
    ),
    (
        "circuit",
        {
            "text": {"prompt": "fine yellow punchy"},
            "motion": {"speed": 1.0, "density": 0.75, "onset_sensitivity": 1.6},
            "palette": {"hue": 0.15, "saturation": 1.3},
            "fx": {"glitch": 0.08},
            "mood": {"valence": 0.5, "arousal": 0.3},
        },
    ),
    (
        "neon_city",
        {
            "text": {"prompt": "neon violet agitated glitchy"},
            "motion": {"speed": 1.5, "density": 0.65, "onset_sensitivity": 1.5},
            "palette": {"hue": 0.85, "saturation": 1.45},
            "fx": {"glitch": 0.4, "chromatic": 0.35},
            "mood": {"valence": 0.4, "arousal": 0.7},
        },
    ),
    # ---- 9–12: post-FX showcase ---- #
    (
        "cosmic",
        {
            "text": {"prompt": "slow violet kaleido sparse"},
            "motion": {"speed": 0.4, "density": 0.25, "onset_sensitivity": 1.0},
            "palette": {"hue": 0.7, "saturation": 1.15},
            "fx": {"kaleidoscope": 6, "chromatic": 0.1},
            "mood": {"valence": -0.1, "arousal": -0.3},
        },
    ),
    (
        "fire",
        {
            "text": {"prompt": "hot intense pulse"},
            "motion": {"speed": 1.3, "density": 0.65, "onset_sensitivity": 1.5},
            "palette": {"hue": 0.02, "saturation": 1.5},
            "fx": {"glitch": 0.1, "chromatic": 0.15},
            "mood": {"valence": 0.8, "arousal": 0.7},
        },
    ),
    (
        "kaleido",
        {
            "text": {"prompt": "fragmented warm dense"},
            "motion": {"speed": 0.9, "density": 0.8, "onset_sensitivity": 1.3},
            "palette": {"hue": 0.06, "saturation": 1.3},
            "fx": {"kaleidoscope": 8},
            "mood": {"valence": 0.5, "arousal": 0.2},
        },
    ),
    (
        "glitch",
        {
            "text": {"prompt": "shattered fragmented broken"},
            "motion": {"speed": 1.4, "density": 0.55, "onset_sensitivity": 1.7},
            "palette": {"saturation": 1.25},
            "fx": {"glitch": 0.6, "chromatic": 0.4, "kaleidoscope": 4},
            "mood": {"valence": 0.0, "arousal": 0.6},
        },
    ),
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
        # If a starter ever drifts out of the schema (e.g., a field gets
        # tightened) Pydantic will raise here at import time; better that
        # than silently shipping a broken starter.
        state = VisualState.model_validate(partial)
        presets.append({"label": label, "state": state.model_dump()})
    # Pad the remaining slots with empties so the user has space for
    # their own saves.
    while len(presets) < PRESET_BANK_SIZE:
        presets.append({"label": "", "state": None})
    return {"version": PRESET_FORMAT_VERSION, "presets": presets}
