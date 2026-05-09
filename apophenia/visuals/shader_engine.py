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

# Preset roster. Each shader is a self-contained fragment-only preset
# using the shared uniform interface (see `shaders/*.frag`).
# All seven are grounded in a maths or physics model:
#   flow         — domain-warped FBM noise field; organic mist
#   prism        — rotating regular-polygon SDF; hard-edged colour shards
#   plasma       — 3-octave FBM metaball; lava-lamp pad texture
#   shock        — interleaved radial sin waves; concentric audio shocks
#   lattice      — animated voronoi diagram; bioluminescent grid
#   curl_noise   — curl of 2D noise (incompressible flow); smoke / vapor
#   quasicrystal — sum of N cosine plane waves at golden-angle
#                  increments; Penrose-style aperiodic interference
PRESETS = (
    "flow",
    "prism",
    "plasma",
    "shock",
    "lattice",
    "curl_noise",
    "quasicrystal",
)


@dataclass
class Layer:
    """One layer in the 14-layer composite.

    `preset` picks which fragment shader runs. `channel` selects which
    audio-source channel (0-indexed) drives the per-frame uniforms.
    """
    preset: str
    channel: int


# Default 14-layer mapping. With 7 presets × 14 channels we land at
# exactly two channels per preset, balanced. Channel groups roughly:
#   Ch1-3:   percussion-flavoured (kick / bass / lead)
#   Ch4:     pad — smooth flowing surface
#   Ch5-8:   percussion / FX channels — mix of organic + structural
#   Ch9-11:  FX bursts — onset-reactive geometry
#   Ch12-14: slow CV / drones — smooth, low-energy textures
DEFAULT_LAYERS: list[Layer] = [
    Layer(preset="shock",         channel=0),    # kick → radial pulse
    Layer(preset="prism",         channel=1),    # bass → rotating polygon
    Layer(preset="quasicrystal",  channel=2),    # lead → aperiodic lattice
    Layer(preset="plasma",        channel=3),    # pad  → smooth plasma
    Layer(preset="curl_noise",    channel=4),    # perc → incompressible flow
    Layer(preset="flow",          channel=5),    # perc → fbm mist
    Layer(preset="lattice",       channel=6),    # perc → voronoi
    Layer(preset="shock",         channel=7),    # perc → radial pulse
    Layer(preset="quasicrystal",  channel=8),    # FX   → aperiodic lattice
    Layer(preset="prism",         channel=9),    # FX   → rotating polygon
    Layer(preset="lattice",       channel=10),   # FX   → voronoi
    Layer(preset="plasma",        channel=11),   # drone → smooth plasma
    Layer(preset="curl_noise",    channel=12),   # drone → incompressible flow
    Layer(preset="flow",          channel=13),   # drone → fbm mist
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

        # Pull per-channel weights + palette hue offset out of the state.
        # `state.palette.hue ∈ [0, 1]` is a hue rotation in turns; we
        # add it as degrees so the shaders' u_hue uniform stays in [0, 360).
        if state is not None:
            channel_weights = list(state.channel_weight)
            hue_offset_deg = float(state.palette.hue) * 360.0
        else:
            channel_weights = [1.0] * 14
            hue_offset_deg = 0.0

        for layer in self.layers:
            ch = layer.channel
            if ch >= len(rms_arr):
                continue

            rms = float(rms_arr[ch])
            cent = float(cent_arr[ch]) if ch < len(cent_arr) else 0.0
            env = float(env_arr[ch]) if ch < len(env_arr) else 0.0
            hue = centroid_to_hue(cent) + hue_offset_deg
            # Normalise into [0, 360) — shader hsv2rgb uses (hue/360)
            hue = hue % 360.0
            weight = (
                float(channel_weights[ch]) if ch < len(channel_weights) else 1.0
            )

            program = self.programs[layer.preset]
            _set_uniform(program, "u_time", time_s)
            _set_uniform(program, "u_resolution", resolution)
            _set_uniform(program, "u_rms", rms)
            _set_uniform(program, "u_centroid", cent)
            _set_uniform(program, "u_onset", env)
            _set_uniform(program, "u_hue", hue)
            _set_uniform(program, "u_channel_weight", weight)
            _set_uniform(program, "u_channel", float(ch))

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


# ---- Post-FX compositor ---- #


class Compositor:
    """Final-stage post-FX pass on the shader-engine output.

    Owns:
      * an offscreen colour FBO that `ShaderEngine` draws into instead of
        the window's default framebuffer (so UV-warp effects can be
        applied to the composite, not per-layer)
      * a fragment-shader Program (`composite.frag`) that runs the full
        kaleidoscope → glitch → chromatic → saturation chain

    Phase 10 strip: the AI texture pair + time-interpolation that lived
    here are gone with the SDXL pipeline. The compositor is now a pure
    UV-warp / colour post-FX layer; whatever the shader engine drew into
    its FBO is what gets warped and shown.

    Lazy FBO resize: the offscreen colour texture is recreated when
    `offscreen_fbo(size)` is called with a different size than last
    time. mglw 3.x doesn't surface a resize notification we can hook,
    so this on-query check is the simplest reliable approach.
    """

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx

        vert_src = (SHADER_DIR / "quad.vert").read_text()
        frag_src = (SHADER_DIR / "composite.frag").read_text()
        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        quad_vertices = np.array(
            [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad_vertices.tobytes())
        self.vao = ctx.simple_vertex_array(self.program, self.vbo, "in_pos")

        # Sampler unit pin — composite.frag only reads u_shader_tex now.
        _set_uniform(self.program, "u_shader_tex", 0)

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
    `mglw.run_window_config(ApopheniaWindow, args=[])` instantiates
    this. moderngl_window doesn't pass our config through __init__, so
    we bridge via class state.

    Phase 10: the rendering path is always shaders → offscreen FBO →
    Compositor (post-FX) → window. The Compositor is unconditional now
    that the AI texture pair is gone — its overhead is one full-screen
    quad pass (~0.1ms at 1080p), trivial against the shader cost.
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
        self.compositor = Compositor(self.ctx)
        self._frame_count = 0
        self._fps_t0 = time.monotonic()
        self._fps_min = math.inf
        # When freeze is on, hold the last (features, time_s) pair so the
        # output is a tableau rather than a black frame. Updated every
        # non-frozen frame.
        self._frozen_features: FastFeatures | None = None
        self._frozen_time: float = 0.0
        logger.info(
            "ShaderEngine ready: %d layers across %d presets%s + post-FX",
            len(self.engine.layers),
            len(self.engine.programs),
            "" if self._state_bus_ref is None else " (state-driven)",
        )

    def on_render(self, time_s: float, frame_time: float) -> None:
        # mglw 3.x renamed `render` → `on_render`. frame_time is the
        # duration of the previous frame in seconds.
        if frame_time > 0:
            self._fps_min = min(self._fps_min, 1.0 / frame_time)

        # Resolve the *current* render-target size. `self.window_size`
        # is a class-attribute that records the **initial requested**
        # size only — it never updates when the user drags the window.
        # `self.wnd.buffer_size` is the live framebuffer size (handles
        # HiDPI: physical pixels, not logical points). On Retina that's
        # ~2× the logical window size, which is what the GL viewport
        # actually needs. The Compositor's offscreen FBO is recreated
        # lazily when this size changes, so resize Just Works.
        size: tuple[int, int] = tuple(self.wnd.buffer_size)  # type: ignore[assignment]

        state = self._state_bus_ref.get() if self._state_bus_ref is not None else None

        if state is not None and state.transport.freeze:
            # Freeze: redraw the last captured features at the last captured
            # time. Channel weights / palette hue can still change while
            # frozen — those are read fresh from `state` each frame.
            features = self._frozen_features
            render_time = self._frozen_time
        else:
            features = self._bus_ref.latest()
            render_time = time_s
            # Cache snapshot for the next freeze window.
            self._frozen_features = features
            self._frozen_time = time_s

        # Pass 1 — shader engine into offscreen FBO.
        fbo = self.compositor.offscreen_fbo(size)
        fbo.use()
        self.ctx.viewport = (0, 0, *size)
        self.engine.render(features, render_time, size, state=state)

        # Pass 2 — composite post-FX to the window.
        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, *size)
        if state is not None:
            saturation = state.palette.saturation
            glitch = state.fx.glitch
            chromatic = state.fx.chromatic
            kaleidoscope = state.fx.kaleidoscope
        else:
            saturation = 1.0
            glitch = 0.0
            chromatic = 0.0
            kaleidoscope = 1
        self.compositor.render(
            saturation=saturation,
            time_s=time_s,
            glitch=glitch,
            chromatic=chromatic,
            kaleidoscope_segments=kaleidoscope,
        )

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
