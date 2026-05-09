"""Global VisualState — pydantic schema, single source of truth for what
the renderer reads each frame.

Phase 10 reshape: the V1 SDXL-Turbo image-generation tier and free-form
text prompts have been removed. "AI视觉" going forward means an AI
layer that controls *shader behaviour* (motion, density, energy
distribution) — not image generation. The schema is now intentionally
minimal: per-channel weights + a few macro modulators (mood XY,
palette, post-FX, transport). Everything here maps directly onto a
GLSL uniform; nothing is prose.

Aesthetic mandate (user-driven): all shader work going forward must
aim for visual beauty, grounded in mathematical / physical models —
fluid dynamics, SDF raymarching, reaction-diffusion, voronoi /
Delaunay, strange attractors, wave equations, etc.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MoodState(BaseModel):
    """Abstract 2D macro. Free for the performer to repurpose; future
    AI-controls-shader work can read it as a coarse summary axis."""

    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.0, ge=-1.0, le=1.0)
    follow_audio: bool = True
    """When True, mood follows audio analysis; when False, manual XY pad wins."""


class PaletteState(BaseModel):
    """Global colour modulation applied across all shader layers."""

    hue: float = Field(0.0, ge=0.0, le=1.0)
    """Hue rotation in turns; 0 = identity. Added to each layer's
    centroid-derived hue at render time."""

    saturation: float = Field(1.0, ge=0.0, le=2.0)
    """Post-composite saturation gain. 1.0 = neutral, 0.0 = greyscale,
    >1.0 = oversaturated."""


class FxState(BaseModel):
    """Final-stage post-FX applied in the Compositor pass."""

    glitch: float = Field(0.0, ge=0.0, le=1.0)
    """Per-row UV displacement intensity; sparse rows trigger so the
    effect reads as bursts rather than a uniform shake."""

    chromatic: float = Field(0.0, ge=0.0, le=1.0)
    """RGB channel separation magnitude; classic lens fringe."""

    kaleidoscope: int = Field(1, ge=1, le=12)
    """Radial mirror segment count; 1 = identity, ≥2 enables fold."""


class TransportState(BaseModel):
    freeze: bool = False
    """When True, the shader engine holds the last (features, time)
    pair so the picture is a tableau. Channel weights / palette / FX
    still update live so the user can sculpt the frozen frame."""


N_CHANNELS = 14


class VisualState(BaseModel):
    """Everything the renderer needs to draw one frame.

    Fields exhaustively cover the live performance surface:
      * channel_weight[14] — per-channel mute / scale
      * mood              — 2D macro
      * palette           — global hue + saturation
      * fx                — post-FX trio
      * transport         — freeze
    """

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
