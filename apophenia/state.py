"""Global VisualState — pydantic schema describing what the renderer
reads each frame.

Phase-10 reshape: dropped fields that only made sense in the V1
SDXL-image architecture (`cfg`, `blend.shader_ai`, `blend.clap_clip`,
`mood.follow_audio`) and added `MotionState` so the AI tier can drive
*shader behaviour* — animation speed, pattern density, onset
sensitivity — instead of generating image content. `mood` is repurposed
as a 2-D motion mood pad: valence biases the palette warmth, arousal
multiplies motion intensity.

This module is the single source of truth for the wire protocol;
breaking changes here also break the on-disk preset format. We don't
ship migration code in V1.5 — older preset files load fine because
Pydantic's default `extra='ignore'` silently drops any field that no
longer exists, and missing new fields fall back to defaults.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextState(BaseModel):
    prompt: str = "soft warm bloom, slow flow"
    """Free-form natural-language prompt. The PromptInterpreter parses it
    into shader-parameter diffs; unknown words are silently ignored."""


class BlendState(BaseModel):
    audio_text: float = Field(0.5, ge=0.0, le=1.0)
    """0 = shaders are purely audio-reactive (motion follows the FeatureBus);
    1 = shaders are prompt-locked (motion follows the prompt-derived state
    only, audio fades out as a modulator). Mid values mix the two."""


class MotionState(BaseModel):
    """How the shader animations behave over time. Phase-10 addition —
    the AI tier writes here instead of producing image bytes."""

    speed: float = Field(1.0, ge=0.0, le=2.0)
    """Global animation-speed multiplier. 1.0 = nominal cadence;
    0 ≈ frozen; 2.0 = double-speed."""

    density: float = Field(0.5, ge=0.0, le=1.0)
    """Pattern density. Used by `lattice` (cell count), `prism` (facet
    count), `flow`/`plasma` (noise frequency), and any future particle
    preset (emission rate). 0 = sparse, 1 = dense."""

    onset_sensitivity: float = Field(1.0, ge=0.0, le=2.0)
    """Multiplier on the per-channel onset envelope before it reaches the
    shaders. 0 = onsets ignored, 1 = nominal, 2 = double-impact."""


class MoodState(BaseModel):
    """2-D motion mood pad — repurposed from the V1 audio-conditioning
    role. Now drives palette warmth + motion arousal as a coarse XY
    override; finer control lives in `motion` and `palette`.
    """

    valence: float = Field(0.0, ge=-1.0, le=1.0)
    """Cool (-1) ↔ warm (+1) palette bias."""

    arousal: float = Field(0.0, ge=-1.0, le=1.0)
    """Calm (-1) ↔ agitated (+1). Multiplies motion.speed and
    motion.onset_sensitivity at the engine boundary."""


class PaletteState(BaseModel):
    hue: float = Field(0.0, ge=0.0, le=1.0)
    saturation: float = Field(1.0, ge=0.0, le=2.0)


class FxState(BaseModel):
    glitch: float = Field(0.0, ge=0.0, le=1.0)
    chromatic: float = Field(0.0, ge=0.0, le=1.0)
    kaleidoscope: int = Field(1, ge=1, le=12)
    """Segment count; 1 = off."""


class TransportState(BaseModel):
    freeze: bool = False


N_CHANNELS = 14


class VisualState(BaseModel):
    """Everything the renderer needs to draw one frame.

    Lives in `StateBus` shared between the control plane (web UI / OSC /
    PromptInterpreter) and the render thread.
    """

    text: TextState = Field(default_factory=TextState)
    blend: BlendState = Field(default_factory=BlendState)
    motion: MotionState = Field(default_factory=MotionState)
    mood: MoodState = Field(default_factory=MoodState)
    channel_weight: list[float] = Field(default_factory=lambda: [1.0] * N_CHANNELS)
    palette: PaletteState = Field(default_factory=PaletteState)
    fx: FxState = Field(default_factory=FxState)
    transport: TransportState = Field(default_factory=TransportState)

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        """Validate channel_weight length matches N_CHANNELS."""
        if len(self.channel_weight) != N_CHANNELS:
            raise ValueError(
                f"channel_weight must have {N_CHANNELS} entries, got {len(self.channel_weight)}"
            )
