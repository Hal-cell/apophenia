"""Shader engine v0 — 14 layers composited additively, driven by the FeatureBus.

Phase 3 surface:
  * 5 fragment-only shader presets (vignette, circle_pulse, horizontal_line,
    bars, noise_sweep) sharing one vertex shader (full-screen quad).
  * 14 `Layer` instances, each binds a preset to one audio channel. The
    default layout is hard-coded; phase 5+ exposes it to the UI.
  * `ShaderEngine` builds one `moderngl.Program` per distinct preset (so a
    layer that re-uses a preset doesn't duplicate the program). Each frame:
    clear → for each layer, set per-channel uniforms → draw the screen quad
    additively.
  * `ApopheniaWindow` is a `moderngl_window.WindowConfig` subclass owning
    the GL context, the engine instance, and the per-frame fps log.

Threading:
  * The window owns the main thread (Cocoa requires GUI on main).
  * `ApopheniaWindow.bus` is a `FeatureBus` populated by the audio worker
    on a daemon thread (set up in `cli.run`).
  * Each render frame calls `bus.latest()` which is a quick mutex-guarded
    read — no contention with the audio thread's publishing.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import moderngl
import moderngl_window as mglw
import numpy as np

if TYPE_CHECKING:
    from apophenia.audio.features_fast import FastFeatures, FeatureBus
    from apophenia.control.state_bus import StateBus
    from apophenia.state import VisualState

logger = logging.getLogger(__name__)

SHADER_DIR = Path(__file__).parent / "shaders"

# ---- Centroid → hue mapping (matches meter UI for visual continuity) ---- #

HUE_LO = 30.0       # warm orange
HUE_HI = 200.0      # cool blue
CENTROID_LO = 50.0
CENTROID_HI = 12_000.0


def centroid_to_hue(hz: float) -> float:
    """Map a spectral centroid in Hz to an HSL hue in [HUE_LO, HUE_HI]."""
    if hz <= CENTROID_LO:
        return HUE_LO
    if hz >= CENTROID_HI:
        return HUE_HI
    f = (hz - CENTROID_LO) / (CENTROID_HI - CENTROID_LO)
    return HUE_LO + f * (HUE_HI - HUE_LO)


# ---- Layer configuration ---- #

# Phase 9 preset roster. Each shader is a self-contained fragment-only
# preset using the shared uniform interface (see `shaders/*.frag`):
#   flow    — domain-warped FBM noise field; organic mist
#   prism   — rotating polygon SDF; hard-edged colour shards
#   plasma  — slow-flowing FBM blob; lava-lamp pad texture
#   shock   — concentric audio-shock waves; great on percussion
#   lattice — animated voronoi cells; bioluminescent grid
PRESETS = ("flow", "prism", "plasma", "shock", "lattice")


@dataclass
class Layer:
    """One layer in the 14-layer composite.

    `preset` picks which fragment shader runs. `channel` selects which
    audio-source channel (0-indexed) drives the per-frame uniforms.
    """
    preset: str
    channel: int


# Default 14-layer mapping for phase 9. Each preset is reused 2-3×
# across 14 channels so visually-similar layers don't pile on top of
# each other.
#
# Ch1-3:   percussion-flavoured (kick / bass / lead) — punchy presets
#          that read well on transients.
# Ch4:     pad — smooth flowing surface for sustained tones.
# Ch5-8:   percussion / FX channels — mix of organic (flow) and
#          structural (lattice / shock) so different rhythms layer.
# Ch9-11:  FX bursts — onset-reactive, expressive.
# Ch12-14: slow CV / drones — quiet smooth presets that don't over-fire.
DEFAULT_LAYERS: list[Layer] = [
    Layer(preset="shock",   channel=0),    # kick     → radial pulse
    Layer(preset="prism",   channel=1),    # bass     → rotating polygon
    Layer(preset="lattice", channel=2),    # lead     → voronoi grid
    Layer(preset="plasma",  channel=3),    # pad      → smooth plasma
    Layer(preset="flow",    channel=4),    # perc     → fbm mist
    Layer(preset="flow",    channel=5),    # perc
    Layer(preset="lattice", channel=6),    # perc
    Layer(preset="shock",   channel=7),    # perc
    Layer(preset="shock",   channel=8),    # FX
    Layer(preset="prism",   channel=9),    # FX
    Layer(preset="lattice", channel=10),   # FX
    Layer(preset="plasma",  channel=11),   # CV / drone
    Layer(preset="plasma",  channel=12),   # CV / drone
    Layer(preset="flow",    channel=13),   # CV / drone
]


# ---- Engine ---- #


class ShaderEngine:
    """Holds GL programs for each preset and renders all layers per frame."""

    def __init__(
        self,
        ctx: moderngl.Context,
        layers: list[Layer] | None = None,
    ) -> None:
        self.ctx = ctx
        self.layers: list[Layer] = list(layers) if layers else list(DEFAULT_LAYERS)

        for layer in self.layers:
            if layer.preset not in PRESETS:
                raise ValueError(
                    f"unknown preset {layer.preset!r}; valid: {PRESETS}"
                )
            if not (0 <= layer.channel < 64):  # liberal upper bound
                raise ValueError(
                    f"layer.channel must be a non-negative int, got {layer.channel}"
                )

        # Build one Program per distinct preset that any layer uses.
        vert_src = (SHADER_DIR / "quad.vert").read_text()
        used = sorted({layer.preset for layer in self.layers})
        self.programs: dict[str, moderngl.Program] = {}
        for name in used:
            frag_src = (SHADER_DIR / f"{name}.frag").read_text()
            self.programs[name] = ctx.program(
                vertex_shader=vert_src,
                fragment_shader=frag_src,
            )

        # Full-screen quad as a triangle strip. Same VBO drives all programs.
        quad_vertices = np.array(
            [-1.0, -1.0,  1.0, -1.0, -1.0,  1.0,  1.0,  1.0],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad_vertices.tobytes())
        self.vaos: dict[str, moderngl.VertexArray] = {
            name: ctx.simple_vertex_array(prog, self.vbo, "in_pos")
            for name, prog in self.programs.items()
        }

    def render(
        self,
        features: FastFeatures | None,
        time_s: float,
        resolution: tuple[int, int],
        state: VisualState | None = None,
    ) -> None:
        """Draw one frame to the currently-bound framebuffer.

        `time_s` is wall-clock seconds since render start. `resolution`
        is the pixel size of the target framebuffer (used for aspect
        correction in shaders). `state` is an optional VisualState that
        applies per-channel weights, palette hue offset, etc.; if None,
        the engine renders with neutral defaults.
        """
        # Clear with full alpha so empty regions are solid black, then
        # additive-blend each layer on top.
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE

        if features is None:
            return  # bus not populated yet

        rms_arr = features.rms or []
        cent_arr = features.centroid or []
        env_arr = features.onset_envelope or []

        # Pull per-channel weights, palette hue offset, and motion params
        # out of the state. Phase-10: `motion.speed` multiplies the time
        # uniform CPU-side so individual shaders' time-based animations
        # all slow/speed up uniformly without each shader needing its
        # own knob. `mood.arousal` multiplies on top so the XY pad acts
        # as a coarse override.
        if state is not None:
            channel_weights = list(state.channel_weight)
            hue_offset_deg = float(state.palette.hue) * 360.0
            arousal_mul = 1.0 + float(state.mood.arousal) * 0.5
            motion_time = time_s * float(state.motion.speed) * arousal_mul
            density = float(state.motion.density)
            onset_gain = float(state.motion.onset_sensitivity) * arousal_mul
        else:
            channel_weights = [1.0] * 14
            hue_offset_deg = 0.0
            motion_time = time_s
            density = 0.5
            onset_gain = 1.0

        for layer in self.layers:
            ch = layer.channel
            if ch >= len(rms_arr):
                continue

            rms = float(rms_arr[ch])
            cent = float(cent_arr[ch]) if ch < len(cent_arr) else 0.0
            env = float(env_arr[ch]) if ch < len(env_arr) else 0.0
            env *= onset_gain  # motion.onset_sensitivity scales the per-channel envelope
            hue = centroid_to_hue(cent) + hue_offset_deg
            # Normalise into [0, 360) — shader hsv2rgb uses (hue/360)
            hue = hue % 360.0
            weight = (
                float(channel_weights[ch]) if ch < len(channel_weights) else 1.0
            )

            program = self.programs[layer.preset]
            _set_uniform(program, "u_time", motion_time)
            _set_uniform(program, "u_resolution", resolution)
            _set_uniform(program, "u_rms", rms)
            _set_uniform(program, "u_centroid", cent)
            _set_uniform(program, "u_onset", env)
            _set_uniform(program, "u_hue", hue)
            _set_uniform(program, "u_channel_weight", weight)
            _set_uniform(program, "u_channel", float(ch))
            _set_uniform(program, "u_density", density)

            self.vaos[layer.preset].render(moderngl.TRIANGLE_STRIP)


def _set_uniform(program: moderngl.Program, name: str, value: object) -> None:
    """Set a uniform if the program declares it; silently ignore otherwise.

    Different presets use different subsets of uniforms (vignette doesn't
    need `u_onset`, bars doesn't need `u_centroid`, etc.). Rather than
    audit each shader, we attempt the write and skip if the uniform was
    optimised out.
    """
    try:
        u = program[name]
    except KeyError:
        return
    try:
        u.value = value
    except (ValueError, TypeError):
        return


# ---- AI compositor ---- #


class Compositor:
    """Final-stage post-FX over the shader-engine FBO.

    Phase-10 reshape: this used to also blend an SDXL-Turbo AI texture,
    but the AI tier was repurposed (it now writes shader *parameters*
    instead of producing image bytes), so the compositor is shader-only.
    Owns:
      * an offscreen colour FBO that ShaderEngine draws into instead of
        the window's default framebuffer
      * a fragment-shader Program (`composite.frag`) that runs the
        kaleidoscope / glitch / chromatic / saturation chain

    The offscreen FBO size follows the window — we recreate it lazily if
    it's queried with a new size. Window resize on mglw 3.x doesn't
    notify us, so this is the cheapest reliable approach.
    """

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx

        # Composite program (single fragment shader sharing quad.vert)
        vert_src = (SHADER_DIR / "quad.vert").read_text()
        frag_src = (SHADER_DIR / "composite.frag").read_text()
        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        quad_vertices = np.array(
            [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad_vertices.tobytes())
        self.vao = ctx.simple_vertex_array(self.program, self.vbo, "in_pos")

        # The composite shader binds one sampler — the shader-engine FBO.
        _set_uniform(self.program, "u_shader_tex", 0)

        # Offscreen FBO + colour texture; lazily recreated on resize.
        self._fbo_size: tuple[int, int] = (0, 0)
        self._shader_tex: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None

    def offscreen_fbo(self, size: tuple[int, int]) -> moderngl.Framebuffer:
        """Return the offscreen FBO, recreating it if `size` changed."""
        if size != self._fbo_size or self._fbo is None:
            if self._shader_tex is not None:
                self._shader_tex.release()
            if self._fbo is not None:
                self._fbo.release()
            self._shader_tex = self.ctx.texture(size, components=4, dtype="f1")
            self._shader_tex.repeat_x = False
            self._shader_tex.repeat_y = False
            self._shader_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._fbo = self.ctx.framebuffer(color_attachments=[self._shader_tex])
            self._fbo_size = size
        return self._fbo

    def render(
        self,
        saturation: float = 1.0,
        time_s: float = 0.0,
        glitch: float = 0.0,
        chromatic: float = 0.0,
        kaleidoscope_segments: int = 1,
    ) -> None:
        """Draw the composite to the currently-bound framebuffer.

        Caller must have already drawn the shader pass into `offscreen_fbo`.
        The default framebuffer should be bound on entry so this writes
        to the visible window.
        """
        # The composite pass is fully opaque — disable blending so a
        # leftover ADD_ALPHA from the shader pass doesn't affect us.
        self.ctx.disable(moderngl.BLEND)

        if self._shader_tex is None:
            return  # offscreen_fbo() never called; nothing to composite
        self._shader_tex.use(location=0)

        _set_uniform(self.program, "u_saturation", float(saturation))
        _set_uniform(self.program, "u_glitch", float(glitch))
        _set_uniform(self.program, "u_chromatic", float(chromatic))
        _set_uniform(self.program, "u_kaleidoscope_segments", int(kaleidoscope_segments))
        _set_uniform(self.program, "u_time", float(time_s))

        self.vao.render(moderngl.TRIANGLE_STRIP)


# ---- moderngl_window glue ---- #


class ApopheniaWindow(mglw.WindowConfig):
    """Render window for live visuals.

    Class attributes (`bus`, `state_bus`) are set by `cli.run` BEFORE
    `mglw.run_window_config(ApopheniaWindow, args=[])` instantiates this.
    moderngl_window doesn't pass our config through __init__, so we
    bridge via class state.
    """

    title = "apophenia"
    window_size = (1920, 1080)
    aspect_ratio: float | None = None  # follow window aspect, no letterboxing
    samples = 4
    resizable = True
    vsync = True
    cursor = True

    # Set externally before the window launches.
    bus: FeatureBus | None = None
    state_bus: StateBus | None = None
    fps_log_period_s: float = 5.0

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if ApopheniaWindow.bus is None:
            raise RuntimeError(
                "ApopheniaWindow.bus must be set before mglw.run_window_config"
            )
        self._bus_ref: FeatureBus = ApopheniaWindow.bus
        self._state_bus_ref: StateBus | None = ApopheniaWindow.state_bus
        self.engine = ShaderEngine(self.ctx)
        # Compositor runs whenever state is available so the kaleidoscope
        # / glitch / chromatic / saturation post-FX work. Without state,
        # we fall back to drawing shaders straight to the window — that
        # path is also what the engine-only GL tests use.
        self.compositor: Compositor | None = (
            Compositor(self.ctx) if self._state_bus_ref is not None else None
        )
        self._frame_count = 0
        self._fps_t0 = time.monotonic()
        self._fps_min = math.inf
        # When freeze is on, hold the last (features, time_s) pair so the
        # output is a tableau rather than a black frame. Updated every
        # non-frozen frame.
        self._frozen_features: FastFeatures | None = None
        self._frozen_time: float = 0.0
        logger.info(
            "ShaderEngine ready: %d layers across %d presets%s%s",
            len(self.engine.layers),
            len(self.engine.programs),
            "" if self._state_bus_ref is None else " (state-driven)",
            " + post-FX compositor" if self.compositor is not None else "",
        )

    def on_render(self, time_s: float, frame_time: float) -> None:
        # mglw 3.x renamed `render` → `on_render`. frame_time is the
        # duration of the previous frame in seconds.
        if frame_time > 0:
            self._fps_min = min(self._fps_min, 1.0 / frame_time)

        state = self._state_bus_ref.get() if self._state_bus_ref is not None else None

        if state is not None and state.transport.freeze:
            # Freeze: redraw the last captured features at the last captured
            # time. Channel weights / palette hue / motion params can still
            # change while frozen — those are read fresh from `state` each
            # frame.
            features = self._frozen_features
            render_time = self._frozen_time
        else:
            features = self._bus_ref.latest()
            render_time = time_s
            # Cache snapshot for the next freeze window.
            self._frozen_features = features
            self._frozen_time = time_s

        if self.compositor is None:
            # No state_bus → no post-FX → render shaders straight to the
            # window (used by tests / headless GL benchmarks).
            self.engine.render(features, render_time, self.window_size, state=state)
        else:
            # Phase-10 path: shaders → offscreen FBO → composite post-FX →
            # window.
            fbo = self.compositor.offscreen_fbo(self.window_size)
            fbo.use()
            self.ctx.viewport = (0, 0, *self.window_size)
            self.engine.render(features, render_time, self.window_size, state=state)

            # Switch back to the default framebuffer for the composite pass.
            self.ctx.screen.use()
            self.ctx.viewport = (0, 0, *self.window_size)

            if state is not None:
                self.compositor.render(
                    saturation=state.palette.saturation,
                    time_s=time_s,
                    glitch=state.fx.glitch,
                    chromatic=state.fx.chromatic,
                    kaleidoscope_segments=state.fx.kaleidoscope,
                )
            else:
                self.compositor.render()  # all-defaults pass-through

        self._frame_count += 1
        now = time.monotonic()
        elapsed = now - self._fps_t0
        if elapsed >= self.fps_log_period_s:
            fps_avg = self._frame_count / elapsed
            logger.info(
                "render fps: avg=%.1f  min=%.1f  (frames=%d, %.1fs)",
                fps_avg,
                self._fps_min,
                self._frame_count,
                elapsed,
            )
            self._frame_count = 0
            self._fps_t0 = now
            self._fps_min = math.inf
