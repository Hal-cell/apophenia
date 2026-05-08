"""Global VisualState — pydantic schema mirroring the OSC intervention protocol.

This is the single source of truth for what the renderer reads each frame.
The control_proc populates it from OSC; the render_proc reads it. Defaults
match `spec/intervention-protocol.md` "Defaults / boot state".
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BlendState(BaseModel):
    audio_text: float = Field(0.5, ge=0.0, le=1.0)
    """0 = pure audio embed, 1 = pure text embed."""

    clap_clip: float = Field(0.5, ge=0.0, le=1.0)
    """Weight of CLAP within the audio embed mix vs raw spectral features."""

    shader_ai: float = Field(0.5, ge=0.0, le=1.0)
    """Final composite mix; 0 = shader only, 1 = AI only."""


class MoodState(BaseModel):
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.0, ge=-1.0, le=1.0)
    follow_audio: bool = True
    """When True, mood is driven by audio CLAP projection; when False, manual XY pad wins."""


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


class TextState(BaseModel):
    prompt: str = "abstract liquid form, subtle iridescent surface"


N_CHANNELS = 14


class VisualState(BaseModel):
    """Everything the renderer needs to draw one frame.

    Lives in shared memory between control_proc and render_proc; updated
    by OSC handlers in control_proc, read each frame by render_proc.
    """

    text: TextState = Field(default_factory=TextState)
    blend: BlendState = Field(default_factory=BlendState)
    cfg: float = Field(5.0, ge=1.0, le=12.0)
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
