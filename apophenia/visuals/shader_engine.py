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
    from apophenia.ai.bus import AIBus, AIFrame
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

PRESETS = ("vignette", "circle_pulse", "horizontal_line", "bars", "noise_sweep")


@dataclass
class Layer:
    """One layer in the 14-layer composite.

    `preset` picks which fragment shader runs. `channel` selects which
    audio-source channel (0-indexed) drives the per-frame uniforms.
    """
    preset: str
    channel: int


# Default 14-layer mapping.
# Ch1-3: percussion-flavoured presets (kick = pulse, bass = line, lead = bars).
# Ch4: pad-flavoured vignette.
# Ch5-8: noise-sweep textures for percussion / FX channels.
# Ch9-11: more circle pulses for FX bursts.
# Ch12-14: vignettes for slow CV-style channels.
DEFAULT_LAYERS: list[Layer] = [
    Layer(preset="circle_pulse",   channel=0),
    Layer(preset="horizontal_line", channel=1),
    Layer(preset="bars",            channel=2),
    Layer(preset="vignette",        channel=3),
    Layer(preset="noise_sweep",     channel=4),
    Layer(preset="noise_sweep",     channel=5),
    Layer(preset="noise_sweep",     channel=6),
    Layer(preset="noise_sweep",     channel=7),
    Layer(preset="circle_pulse",    channel=8),
    Layer(preset="circle_pulse",    channel=9),
    Layer(preset="circle_pulse",    channel=10),
    Layer(preset="vignette",        channel=11),
    Layer(preset="vignette",        channel=12),
    Layer(preset="vignette",        channel=13),
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


# ---- AI compositor ---- #


class Compositor:
    """Final-stage composite: shader FBO + AI textures + post-FX.

    Owns:
      * an offscreen colour FBO that ShaderEngine draws into instead of
        the window's default framebuffer
      * **two** AI textures — `prev` and `current` — so the composite
        shader can crossfade between successive SDXL gens (otherwise raw
        cuts at 5–15 fps look like a slideshow)
      * a fragment-shader Program (`composite.frag`) that runs the full
        kaleidoscope / glitch / chromatic / saturation chain

    Time-interpolation between AI frames is driven by a monotonic clock
    captured in `maybe_upload_ai_frame()`. Each render call recomputes
    `ai_interp ∈ [0, 1]` from elapsed wallclock seconds divided by the
    estimated AI period (smoothed from observed `latency_ms`).

    The offscreen FBO size follows the window — we recreate it lazily if
    it's queried with a new size. Window resize on mglw 3.x doesn't
    notify us, so this is the cheapest reliable approach.

    AI-texture swap (no GPU-to-GPU copy): we hold two textures in a list
    and flip an index each upload. The "current" texture is the one we
    just wrote to; the "prev" one still holds whatever we wrote there
    on the *previous* upload — exactly the predecessor frame.
    """

    # Interpolation period default. SDXL-Turbo on M3 Max produces a frame
    # every ~70–200ms; if `latency_ms` arrives in the AIFrame we adapt
    # to it via an exponential moving average.
    DEFAULT_AI_PERIOD_S = 0.2
    AI_PERIOD_EMA_ALPHA = 0.3  # how aggressively to track latency changes

    def __init__(self, ctx: moderngl.Context, ai_resolution: int = 512) -> None:
        self.ctx = ctx
        self.ai_resolution = ai_resolution

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

        # Bind sampler units explicitly so the fragment shader can `texture()`
        # on `u_shader_tex` (unit 0), `u_ai_tex_prev` (unit 1) and
        # `u_ai_tex_cur` (unit 2).
        _set_uniform(self.program, "u_shader_tex", 0)
        _set_uniform(self.program, "u_ai_tex_prev", 1)
        _set_uniform(self.program, "u_ai_tex_cur", 2)

        # Offscreen FBO + colour texture; lazily recreated on resize.
        self._fbo_size: tuple[int, int] = (0, 0)
        self._shader_tex: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None

        # AI textures: pair of (1x1 black) placeholders so the shader has
        # something valid to sample on cold start. Both default to black so
        # the crossfade is invisible until real frames land.
        self._ai_textures: list[moderngl.Texture] = [
            self._fresh_ai_texture((1, 1)) for _ in range(2)
        ]
        for t in self._ai_textures:
            t.write(b"\x00\x00\x00")
        # `_cur_idx` points at the texture that holds the most recent
        # frame; the other index is "prev".
        self._cur_idx = 0
        self._last_ai_gen = 0
        self._last_ai_upload_t: float | None = None
        self._ai_period_s = self.DEFAULT_AI_PERIOD_S

    def _fresh_ai_texture(self, size: tuple[int, int]) -> moderngl.Texture:
        tex = self.ctx.texture(size, components=3, dtype="f1")
        tex.repeat_x = False
        tex.repeat_y = False
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return tex

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

    def maybe_upload_ai_frame(self, frame: AIFrame | None) -> bool:
        """Promote a fresh AIFrame onto the GPU.

        Strategy: flip `_cur_idx` so what *was* current is now "prev"
        (still holding the old bytes in its texture), then upload the
        new image into the new "current" slot. No GPU→GPU copy needed.

        Special case: on the very first upload there is no real "prev",
        so we write the same bytes to *both* textures — that way the
        first frame's crossfade is a no-op rather than fading from the
        initial black placeholder.

        Returns True iff we actually uploaded.
        """
        if frame is None or frame.image is None:
            return False
        if frame.gen_count == self._last_ai_gen:
            return False
        h, w = int(frame.image.shape[0]), int(frame.image.shape[1])
        is_first = self._last_ai_gen == 0
        # Flip — the texture at the *new* _cur_idx is the one we'll write
        # into. The texture at (1 - _cur_idx) keeps its previous bytes
        # and becomes our "prev" sampler.
        self._cur_idx = 1 - self._cur_idx
        target = self._ai_textures[self._cur_idx]
        if (w, h) != target.size:
            target.release()
            target = self._fresh_ai_texture((w, h))
            self._ai_textures[self._cur_idx] = target
        payload = frame.image.tobytes()
        target.write(payload)
        if is_first:
            # Seed `prev` with the same bytes so frame #1 doesn't crossfade
            # out of black. We may need to resize prev to match.
            other = self._ai_textures[1 - self._cur_idx]
            if (w, h) != other.size:
                other.release()
                other = self._fresh_ai_texture((w, h))
                self._ai_textures[1 - self._cur_idx] = other
            other.write(payload)

        # Track timing for interpolation.
        now = time.monotonic()
        if self._last_ai_upload_t is not None:
            observed = now - self._last_ai_upload_t
            # Clamp the observation so a long pause (frozen prompt etc.)
            # doesn't push the EMA off into stale territory.
            observed = max(0.05, min(observed, 1.0))
            self._ai_period_s = (
                (1.0 - self.AI_PERIOD_EMA_ALPHA) * self._ai_period_s
                + self.AI_PERIOD_EMA_ALPHA * observed
            )
        # As a fallback, latency_ms (when present) gives us a useful
        # initial estimate for the very first frame — saves us a frame
        # of "no interp because period unknown".
        elif frame.latency_ms > 0:
            self._ai_period_s = max(0.05, min(frame.latency_ms / 1000.0, 1.0))
        self._last_ai_upload_t = now
        self._last_ai_gen = frame.gen_count
        return True

    def render(
        self,
        blend: float,
        saturation: float,
        has_ai: bool,
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
        # `prev` lives at the *other* index from `_cur_idx`.
        self._ai_textures[1 - self._cur_idx].use(location=1)
        self._ai_textures[self._cur_idx].use(location=2)

        # Compute crossfade factor from elapsed wallclock.
        if self._last_ai_upload_t is None:
            ai_interp = 1.0  # no AI yet → just show "current" (black anyway)
        else:
            elapsed = time.monotonic() - self._last_ai_upload_t
            ai_interp = max(0.0, min(elapsed / max(self._ai_period_s, 1e-3), 1.0))

        _set_uniform(self.program, "u_blend", float(blend))
        _set_uniform(self.program, "u_saturation", float(saturation))
        _set_uniform(self.program, "u_has_ai", 1.0 if has_ai else 0.0)
        _set_uniform(self.program, "u_ai_interp", float(ai_interp))
        _set_uniform(self.program, "u_glitch", float(glitch))
        _set_uniform(self.program, "u_chromatic", float(chromatic))
        _set_uniform(self.program, "u_kaleidoscope_segments", int(kaleidoscope_segments))
        _set_uniform(self.program, "u_time", float(time_s))

        self.vao.render(moderngl.TRIANGLE_STRIP)


# ---- moderngl_window glue ---- #


class ApopheniaWindow(mglw.WindowConfig):
    """Render window for live visuals.

    Class attributes (`bus`, `state_bus`, `requested_size`) are set by
    `cli.run` BEFORE `mglw.run_window_config(ApopheniaWindow, args=[])`
    instantiates this. moderngl_window doesn't pass our config through
    __init__, so we bridge via class state.
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
    ai_bus: AIBus | None = None
    fps_log_period_s: float = 5.0

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if ApopheniaWindow.bus is None:
            raise RuntimeError(
                "ApopheniaWindow.bus must be set before mglw.run_window_config"
            )
        self._bus_ref: FeatureBus = ApopheniaWindow.bus
        self._state_bus_ref: StateBus | None = ApopheniaWindow.state_bus
        self._ai_bus_ref: AIBus | None = ApopheniaWindow.ai_bus
        self.engine = ShaderEngine(self.ctx)
        # Compositor only spins up when AI is enabled; without it we keep
        # the phase-3 fast path of drawing shaders straight to the window.
        self.compositor: Compositor | None = (
            Compositor(self.ctx) if self._ai_bus_ref is not None else None
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
            " + AI compositor" if self.compositor is not None else "",
        )

    def on_render(self, time_s: float, frame_time: float) -> None:
        # mglw 3.x renamed `render` → `on_render`. frame_time is the
        # duration of the previous frame in seconds.
        if frame_time > 0:
            self._fps_min = min(self._fps_min, 1.0 / frame_time)

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

        if self.compositor is None:
            # Phase-3 fast path: shaders go straight to the window.
            self.engine.render(features, render_time, self.window_size, state=state)
        else:
            # Phase-6+ path: shaders → offscreen FBO → composite (with
            # post-FX) → window.
            fbo = self.compositor.offscreen_fbo(self.window_size)
            fbo.use()
            self.ctx.viewport = (0, 0, *self.window_size)
            self.engine.render(features, render_time, self.window_size, state=state)

            # Pull the latest AI frame; the compositor decides whether
            # there's anything new to upload.
            ai_frame = self._ai_bus_ref.latest() if self._ai_bus_ref is not None else None
            self.compositor.maybe_upload_ai_frame(ai_frame)

            # Switch back to the default framebuffer for the composite pass.
            self.ctx.screen.use()
            self.ctx.viewport = (0, 0, *self.window_size)

            # Pull all the post-FX uniforms from state (with neutral
            # fallbacks when state is missing).
            if state is not None:
                blend = state.blend.shader_ai
                saturation = state.palette.saturation
                glitch = state.fx.glitch
                chromatic = state.fx.chromatic
                kaleidoscope = state.fx.kaleidoscope
            else:
                blend = 0.0
                saturation = 1.0
                glitch = 0.0
                chromatic = 0.0
                kaleidoscope = 1
            has_ai = ai_frame is not None
            self.compositor.render(
                blend=blend,
                saturation=saturation,
                has_ai=has_ai,
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
