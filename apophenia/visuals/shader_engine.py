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
        self._frame_count = 0
        self._fps_t0 = time.monotonic()
        self._fps_min = math.inf
        # When freeze is on, hold the last (features, time_s) pair so the
        # output is a tableau rather than a black frame. Updated every
        # non-frozen frame.
        self._frozen_features: FastFeatures | None = None
        self._frozen_time: float = 0.0
        logger.info(
            "ShaderEngine ready: %d layers across %d presets%s",
            len(self.engine.layers),
            len(self.engine.programs),
            "" if self._state_bus_ref is None else " (state-driven)",
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

        self.engine.render(features, render_time, self.window_size, state=state)

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
