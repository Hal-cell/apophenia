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

from typing import Literal

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

    trail: float = Field(0.0, ge=0.0, le=0.99)
    """Frame-to-frame feedback decay. 0 = no trail (each frame stands
    alone). Approaching 1 = trails persist across many frames. Capped
    at 0.99 to avoid an infinite-energy feedback loop."""


class TransportState(BaseModel):
    freeze: bool = False


class ForceState(BaseModel):
    """Phase-14 fluid-cluster force model. Each particle receives the
    sum of these forces every step; the result is then clamped to
    `max_speed` for terminal-velocity behaviour.

    Defaults are tuned for the TD-cluster + Ikeda-density aesthetic:
    moderate cohesion (particles cluster around their emitter rather
    than scattering), moderate noise (organic flow lines), gentle
    vortex (slow rotation rather than tornado), and a max_speed of
    2.0 world-units/sec so particles never feel ballistic.
    """

    noise: float = Field(0.5, ge=0.0, le=1.0)
    """Curl-noise / flow-field strength. 0 = particles ballistic;
    1 = strong organic flow that bends every trajectory."""

    vortex: float = Field(0.4, ge=0.0, le=1.0)
    """Tangential rotation around each particle's emitter (axis = world
    Y). 0 = no spin; 1 = tight whirlpool around each emitter."""

    cohesion: float = Field(0.5, ge=0.0, le=1.0)
    """Pull toward emitter — the cluster lever. 0 = particles drift
    away forever; 1 = they hug the emitter tightly. Phase-14 default
    of 0.5 gives a TD-style breathing cluster."""

    max_speed: float = Field(2.0, ge=0.5, le=8.0)
    """Terminal velocity cap (world-units / sec). Forces particles
    into a fluid-like flow rather than letting them accelerate
    indefinitely."""

    streak_length: float = Field(0.06, ge=0.0, le=0.5)
    """Phase-16 visual: how long each particle's velocity-aligned
    streak is, in *seconds of motion*. The render shader places the
    streak's tail at `pos - vel × streak_length`. 0 = points (no
    streak), 0.5 = dramatic flow lines. Default 0.06 gives a subtle
    motion-blur feel without overwhelming the cluster shape."""


class EmitterState(BaseModel):
    """Phase-17: how the 14 audio-channel emitters are arranged in 3D
    space, and whether they move over time.

    Five built-in patterns shape the static base positions:
      * `ring`      — phase 12 default; XZ-plane circle radius 1.6
      * `grid`      — 7×2 grid; horizontal arrangement
      * `line`      — single horizontal line along X axis
      * `sphere`    — fibonacci-spiral distribution on a sphere
      * `lissajous` — 3D lissajous curve

    On top of the base, each emitter drifts on a per-channel
    Lissajous orbit. `motion_amp` scales the orbit radius, `motion_speed`
    the angular rate. `radius` scales the entire pattern uniformly.
    """

    pattern: Literal["ring", "grid", "line", "sphere", "lissajous"] = "ring"
    motion_amp: float = Field(0.0, ge=0.0, le=1.0)
    """How much each emitter wanders around its base position. 0 = static
    (matches phase-12/13/14/15/16 behaviour); 1 = wide swing."""

    motion_speed: float = Field(0.5, ge=0.0, le=2.0)
    """Angular rate of the per-emitter drift orbit, revolutions/sec."""

    radius: float = Field(1.6, ge=0.5, le=4.0)
    """Uniform scale on the base pattern. The original ring had radius
    1.6; smaller values pull all emitters in toward the origin."""


class CameraState(BaseModel):
    """3D camera around the particle world. Phase-12 addition.

    The 14 audio-channel emitters live on a ring around the origin in
    the XZ plane; the camera looks at that origin from `distance`
    units away, tilted up by `elevation` degrees, optionally orbiting
    at `orbit_speed` revolutions per second.
    """

    distance: float = Field(5.0, ge=1.5, le=20.0)
    """Camera radius from origin (the centre of the emitter ring)."""

    elevation: float = Field(15.0, ge=-89.0, le=89.0)
    """Degrees above (positive) / below the horizon."""

    orbit_speed: float = Field(0.05, ge=-2.0, le=2.0)
    """Revolutions per second when `autorotate` is on. Negative = reverse."""

    fov_deg: float = Field(60.0, ge=20.0, le=120.0)
    """Vertical field of view in degrees. Narrow → tighter, telephoto;
    wide → fish-eye-ish."""

    autorotate: bool = True
    """Whether the camera orbits the origin continuously. When False,
    the camera holds at the orbit angle from the most recent `time` it
    saw — i.e. freezes in place."""


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
    camera: CameraState = Field(default_factory=CameraState)
    force: ForceState = Field(default_factory=ForceState)
    emitter: EmitterState = Field(default_factory=EmitterState)

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        """Validate channel_weight length matches N_CHANNELS."""
        if len(self.channel_weight) != N_CHANNELS:
            raise ValueError(
                f"channel_weight must have {N_CHANNELS} entries, got {len(self.channel_weight)}"
            )
