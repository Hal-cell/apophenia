"""Curated 12-preset starter bank shipped with the package.

This is the V1 first-run experience: when a user installs apophenia and
there's no `~/.config/apophenia/presets.json` yet, `presets.load()`
materialises this bank to disk so the preset grid in the UI is alive
on first launch instead of empty.

The first 12 slots cover a deliberate spread:
  * 1–4   minimal / quiet → busy / loud (level along the "energy" axis)
  * 5–8   organic / natural → digital / synthetic (along "synthetic-ness")
  * 9–12  experimental territories that show off post-FX
Slots 13–16 ship empty so the user has space for their own without
having to first delete an existing one.

Each slot is a complete `VisualState` snapshot — prompt + every slider /
knob / FX / channel weight — captured with the schema's defaults filled
in. To tweak the bank, edit `STARTER_DATA` below and the change ships
in the next install. Existing users keep their saved-over slots.
"""

from __future__ import annotations

from typing import Any

# Each entry is (label, partial state dict). The partial is deep-merged
# onto VisualState defaults at materialisation time, so any field omitted
# inherits its default from the schema.
STARTER_DATA: list[tuple[str, dict[str, Any]]] = [
    # ---- 1–4: energy axis (minimal → loud) ---- #
    (
        "bloom",
        {
            "text": {"prompt": "soft lavender clouds at dawn, bokeh light, dreamy haze"},
            "blend": {"audio_text": 0.45, "shader_ai": 0.55},
            "cfg": 4.0,
            "palette": {"hue": 0.05, "saturation": 0.85},
        },
    ),
    (
        "paper",
        {
            "text": {
                "prompt": (
                    "torn paper textures, watercolor stains, "
                    "delicate ink wash, asian calligraphy"
                ),
            },
            "blend": {"audio_text": 0.6, "shader_ai": 0.3},  # shader-heavy
            "cfg": 4.5,
            "palette": {"saturation": 0.7},
        },
    ),
    (
        "liquid_metal",
        {
            "text": {
                "prompt": (
                    "molten chrome surface, slow ripples, reflective, "
                    "studio lighting, hyperreal"
                ),
            },
            "blend": {"audio_text": 0.55, "shader_ai": 0.65},
            "cfg": 5.0,
            "palette": {"saturation": 1.1},
            "fx": {"chromatic": 0.1},
        },
    ),
    (
        "cathedral",
        {
            "text": {
                "prompt": (
                    "molten glass cathedral, deep violet, ribbons of fire, "
                    "ornate baroque, 35mm film grain"
                ),
            },
            "blend": {"audio_text": 0.7, "shader_ai": 0.6},
            "cfg": 6.0,
            "palette": {"hue": 0.7, "saturation": 1.2},
            "fx": {"glitch": 0.05},
        },
    ),
    # ---- 5–8: organic → synthetic ---- #
    (
        "forest",
        {
            "text": {
                "prompt": (
                    "ancient redwood forest in mist, shafts of light through leaves, "
                    "moss, cinematic"
                ),
            },
            "blend": {"audio_text": 0.5, "shader_ai": 0.55},
            "cfg": 5.0,
            "palette": {"hue": 0.3, "saturation": 1.0},
            "fx": {"chromatic": 0.05},
        },
    ),
    (
        "coral",
        {
            "text": {
                "prompt": (
                    "underwater coral reef, schools of fish, soft caustics, "
                    "bioluminescent"
                ),
            },
            "blend": {"audio_text": 0.55, "shader_ai": 0.5},
            "cfg": 5.5,
            "palette": {"hue": 0.55, "saturation": 1.15},
            "fx": {"chromatic": 0.15},
        },
    ),
    (
        "circuit",
        {
            "text": {
                "prompt": (
                    "circuit board macro, gold traces, intricate geometric pattern, "
                    "high contrast"
                ),
            },
            "blend": {"audio_text": 0.65, "shader_ai": 0.7},
            "cfg": 5.5,
            "palette": {"hue": 0.13, "saturation": 1.3},
            "fx": {"glitch": 0.08},
        },
    ),
    (
        "neon_city",
        {
            "text": {
                "prompt": (
                    "cyberpunk city at night, rain, neon reflections on wet asphalt, "
                    "anamorphic flares"
                ),
            },
            "blend": {"audio_text": 0.7, "shader_ai": 0.75},
            "cfg": 6.5,
            "palette": {"hue": 0.85, "saturation": 1.4},
            "fx": {"glitch": 0.15, "chromatic": 0.25},
        },
    ),
    # ---- 9–12: post-FX territory ---- #
    (
        "cosmic",
        {
            "text": {
                "prompt": (
                    "spiral galaxy core, nebulae, deep space, billions of stars, "
                    "cinematic, hubble"
                ),
            },
            "blend": {"audio_text": 0.5, "shader_ai": 0.55},
            "cfg": 5.0,
            "palette": {"hue": 0.7, "saturation": 1.2},
            "fx": {"kaleidoscope": 6, "chromatic": 0.1},
        },
    ),
    (
        "fire",
        {
            "text": {
                "prompt": (
                    "raging bonfire, dancing embers, dark background, "
                    "long exposure, abstract"
                ),
            },
            "blend": {"audio_text": 0.6, "shader_ai": 0.6},
            "cfg": 5.0,
            "palette": {"hue": 0.05, "saturation": 1.5},
            "fx": {"glitch": 0.1, "chromatic": 0.15},
        },
    ),
    (
        "kaleido",
        {
            "text": {
                "prompt": (
                    "ornate persian rug pattern, jewel tones, kaleidoscopic, "
                    "gold thread, intricate"
                ),
            },
            "blend": {"audio_text": 0.55, "shader_ai": 0.6},
            "cfg": 5.0,
            "palette": {"saturation": 1.3},
            "fx": {"kaleidoscope": 8},
        },
    ),
    (
        "glitch",
        {
            "text": {
                "prompt": (
                    "vhs glitch art, signal corruption, scan lines, "
                    "magnetic distortion, broken tv"
                ),
            },
            "blend": {"audio_text": 0.65, "shader_ai": 0.7},
            "cfg": 5.5,
            "palette": {"saturation": 1.25},
            "fx": {"glitch": 0.5, "chromatic": 0.4},
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
