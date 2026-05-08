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
    # ---- 1–4: cluster shapes ---- #
    (
        "ikeda",  # tight monochrome data cluster (Ryoji Ikeda reference)
        {
            "text": {"prompt": "ikeda dense data tight"},
            "force": {"cohesion": 0.85, "vortex": 0.15, "noise": 0.25,
                      "max_speed": 1.0},
            "motion": {"density": 0.95, "speed": 0.6, "onset_sensitivity": 1.2},
            "palette": {"saturation": 0.15},
            "camera": {"distance": 4.5, "elevation": 5.0, "orbit_speed": 0.04},
        },
    ),
    (
        "fluid",  # TD-cluster-style flowing liquid
        {
            "text": {"prompt": "fluid flowing cohesive"},
            "force": {"cohesion": 0.6, "vortex": 0.35, "noise": 0.7,
                      "max_speed": 1.8},
            "motion": {"density": 0.7, "speed": 0.9},
            "palette": {"saturation": 0.6},
            "camera": {"distance": 5.5, "elevation": 20.0, "orbit_speed": 0.05},
        },
    ),
    (
        "tornado",  # tight whirlpool around emitters
        {
            "text": {"prompt": "tornado tight close pulsing"},
            "force": {"cohesion": 0.7, "vortex": 0.95, "noise": 0.4,
                      "max_speed": 3.0},
            "motion": {"density": 0.8, "onset_sensitivity": 1.6},
            "palette": {"saturation": 0.7},
            "camera": {"distance": 3.5, "elevation": 25.0, "orbit_speed": 0.12},
            "mood": {"arousal": 0.7},
        },
    ),
    (
        "exploding",  # anti-cluster: scatter outward on every hit
        {
            "text": {"prompt": "exploding volatile dispersed"},
            "force": {"cohesion": 0.05, "vortex": 0.15, "noise": 0.5,
                      "max_speed": 5.0},
            "motion": {"density": 0.7, "onset_sensitivity": 1.7,
                       "speed": 1.4},
            "palette": {"saturation": 0.85},
            "camera": {"distance": 7.0, "elevation": 15.0, "orbit_speed": 0.08},
            "mood": {"arousal": 0.9},
        },
    ),
    # ---- 5–8: motion / energy levels ---- #
    (
        "drifting",  # quiet, slow, sparse — meditative
        {
            "text": {"prompt": "calm drifting sparse cool"},
            "force": {"cohesion": 0.4, "vortex": 0.2, "noise": 0.5,
                      "max_speed": 1.2},
            "motion": {"density": 0.35, "speed": 0.5},
            "palette": {"hue": 0.55, "saturation": 0.4},
            "camera": {"distance": 6.0, "elevation": 10.0, "orbit_speed": 0.03},
            "mood": {"valence": -0.2, "arousal": -0.4},
        },
    ),
    (
        "breathing",  # slow modulating cluster, mid-density
        {
            "text": {"prompt": "breathing reactive pulsing"},
            "force": {"cohesion": 0.7, "vortex": 0.3, "noise": 0.45,
                      "max_speed": 1.6},
            "motion": {"density": 0.6, "onset_sensitivity": 1.0,
                       "speed": 0.7},
            "palette": {"saturation": 0.5},
            "camera": {"distance": 5.0, "elevation": 18.0, "orbit_speed": 0.04},
            "mood": {"arousal": 0.3},
        },
    ),
    (
        "swirling",  # whirlpool-ish, mid orbit
        {
            "text": {"prompt": "swirling vortex flowing"},
            "force": {"cohesion": 0.55, "vortex": 0.7, "noise": 0.5,
                      "max_speed": 2.5},
            "motion": {"density": 0.65, "speed": 1.1},
            "palette": {"saturation": 0.65},
            "camera": {"distance": 5.0, "orbit_speed": 0.18, "elevation": 25.0},
        },
    ),
    (
        "stormy",  # high-energy chaotic
        {
            "text": {"prompt": "stormy chaotic turbulent"},
            "force": {"cohesion": 0.3, "vortex": 0.6, "noise": 0.95,
                      "max_speed": 4.0},
            "motion": {"density": 0.75, "onset_sensitivity": 1.5,
                       "speed": 1.5},
            "palette": {"saturation": 0.7},
            "camera": {"distance": 6.5, "elevation": 30.0, "orbit_speed": 0.15},
            "mood": {"arousal": 0.8},
        },
    ),
    # ---- 9–12: post-FX + camera angle showcases ---- #
    (
        "cosmic",  # very slow, kaleidoscope, cool
        {
            "text": {"prompt": "slow cool kaleido"},
            "force": {"cohesion": 0.6, "vortex": 0.25, "noise": 0.4,
                      "max_speed": 1.4},
            "motion": {"density": 0.5, "speed": 0.5},
            "palette": {"hue": 0.6, "saturation": 0.6},
            "fx": {"kaleidoscope": 6, "chromatic": 0.1},
            "camera": {"distance": 7.0, "elevation": 20.0, "orbit_speed": 0.04},
        },
    ),
    (
        "fire",  # hot intense cluster
        {
            "text": {"prompt": "hot intense pulsing tight"},
            "force": {"cohesion": 0.75, "vortex": 0.6, "noise": 0.5,
                      "max_speed": 2.5},
            "motion": {"density": 0.7, "onset_sensitivity": 1.5,
                       "speed": 1.2},
            "palette": {"hue": 0.02, "saturation": 1.0},
            "fx": {"chromatic": 0.15},
            "camera": {"distance": 4.0, "elevation": 12.0, "orbit_speed": 0.08},
            "mood": {"arousal": 0.6},
        },
    ),
    (
        "ghost",  # long trails over slow cluster
        {
            "text": {"prompt": "ghost lingering breathing"},
            "force": {"cohesion": 0.55, "vortex": 0.3, "noise": 0.4,
                      "max_speed": 1.5},
            "motion": {"density": 0.55, "speed": 0.7,
                       "onset_sensitivity": 0.9},
            "palette": {"saturation": 0.4},
            "fx": {"trail": 0.85, "chromatic": 0.1},
            "camera": {"distance": 5.5, "elevation": 15.0, "orbit_speed": 0.04},
        },
    ),
    (
        "glitch",  # broken / shattered
        {
            "text": {"prompt": "shattered broken volatile"},
            "force": {"cohesion": 0.3, "vortex": 0.5, "noise": 0.7,
                      "max_speed": 3.5},
            "motion": {"density": 0.6, "onset_sensitivity": 1.7,
                       "speed": 1.3},
            "palette": {"saturation": 0.85},
            "fx": {"glitch": 0.6, "chromatic": 0.4, "kaleidoscope": 4},
            "camera": {"distance": 5.0, "orbit_speed": 0.18},
            "mood": {"arousal": 0.7},
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
