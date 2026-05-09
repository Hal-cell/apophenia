"""Global VisualState — pydantic schema, single source of truth for what
the renderer reads each frame.

Phase 13 reshape: removed the V1 control surface entirely (web UI,
sliders, presets, mood XY pad). The state is now produced by an
autopilot Modulator (`apophenia.autopilot.Modulator`) from
`(wallclock_time, audio_features)` — no human input. Schema is a
direct mirror of the GLSL uniforms the shader engine + compositor
consume each frame.

Aesthetic mandate: shaders are math/physics-grounded (FBM curl
noise, voronoi, polygon SDF, plane-wave quasicrystal interference,
golden-angle phyllotaxis-style lattices). Going forward all new
visuals stay in this lineage.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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

    bloom: float = Field(0.3, ge=0.0, le=1.0)
    """High-pass glow that bleeds bright pixels into their neighbourhood
    via 24-tap Poisson-disk Gaussian over mipmap level 2 of the shader
    FBO. Default 0.3 = tasteful baseline."""

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
    still update live so the modulator can sculpt the frozen frame."""


N_CHANNELS = 14


class VisualState(BaseModel):
    """Everything the renderer needs to draw one frame.

    Built per-frame by `apophenia.autopilot.Modulator.state(t, features)`.
    Fields:
      * channel_weight[14] — Gaussian "spotlight" wandering across channels
      * palette            — global hue + saturation
      * fx                 — bloom / glitch / chromatic / kaleidoscope
      * transport          — freeze (rare; for tableau moments)
    """

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
