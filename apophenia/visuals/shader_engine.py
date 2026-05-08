"""GL host: post-FX compositor + moderngl_window glue.

Phase-14 reshape: the 2D shader engine (14 fragment-shader layers
composited additively) was removed entirely. The render path is now
particle-only — `ParticleEngine` writes its 3D output directly into
the compositor's offscreen FBO, and the post-FX chain (kaleidoscope /
glitch / chromatic / saturation / trail feedback) runs over that.

The file is named `shader_engine.py` for git-history continuity; its
content is now the GL host wiring around the particle world.

Threading:
  * The window owns the main thread (Cocoa requires GUI on main).
  * `ApopheniaWindow.bus / state_bus / slow_bus` are populated by
    daemon threads (audio fast / control HTTP / audio slow).
  * Each render frame reads `bus.latest()` and friends — quick
    mutex-guarded reads with no contention.
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING

import moderngl
import moderngl_window as mglw
import numpy as np

if TYPE_CHECKING:
    from apophenia.audio.features_fast import FastFeatures, FeatureBus
    from apophenia.audio.features_slow import SlowBus
    from apophenia.control.state_bus import StateBus

logger = logging.getLogger(__name__)

SHADER_DIR = Path(__file__).parent / "shaders"


# --------------------------------------------------------------------------- #
# Uniform helper
# --------------------------------------------------------------------------- #


def _set_uniform(program: moderngl.Program, name: str, value: object) -> None:
    """Set a uniform if the program declares it; silently ignore otherwise.

    Programs may strip unused uniforms during compilation; trying to write
    them would raise. The compositor + feedback pipeline shares helper
    code that touches a superset of uniforms, so this guard keeps the
    plumbing simple.
    """
    try:
        u = program[name]
    except KeyError:
        return
    try:
        u.value = value
    except (ValueError, TypeError):
        return


# --------------------------------------------------------------------------- #
# Compositor — post-FX over the offscreen FBO
# --------------------------------------------------------------------------- #


class Compositor:
    """Final-stage post-FX over the offscreen FBO that the particle
    engine drew into. Runs the kaleidoscope → glitch → chromatic →
    saturation chain plus optional frame-to-frame feedback (trail).

    Owns:
      * an offscreen colour FBO + texture (the shared "render target"
        the particle engine writes into)
      * a ping-pong pair of feedback FBOs/textures for trail accumulation
      * two fragment-shader Programs — `feedback.frag` (max-blend with
        decay) and `composite.frag` (post-FX chain)

    All FBOs follow the window size; recreated lazily on resize. The
    compositor used to be named after the (now-deleted) 14-layer
    fragment-shader pipeline; phase-14 left only the post-FX role.
    """

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx

        vert_src = (SHADER_DIR / "quad.vert").read_text()
        composite_src = (SHADER_DIR / "composite.frag").read_text()
        feedback_src = (SHADER_DIR / "feedback.frag").read_text()

        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=composite_src)
        self.feedback_program = ctx.program(
            vertex_shader=vert_src, fragment_shader=feedback_src
        )

        quad_vertices = np.array(
            [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad_vertices.tobytes())
        self.vao = ctx.simple_vertex_array(self.program, self.vbo, "in_pos")
        self.feedback_vao = ctx.simple_vertex_array(
            self.feedback_program, self.vbo, "in_pos"
        )

        # Sampler unit assignments — composite reads unit 0, feedback
        # reads unit 0 (shader) + unit 1 (prev feedback).
        _set_uniform(self.program, "u_shader_tex", 0)
        _set_uniform(self.feedback_program, "u_shader_tex", 0)
        _set_uniform(self.feedback_program, "u_prev_feedback", 1)

        # Offscreen FBO for the render pass; lazily recreated on resize.
        # Despite the name, this is the *combined* render target — the
        # particle engine writes into it and the compositor samples it.
        self._fbo_size: tuple[int, int] = (0, 0)
        self._shader_tex: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None

        # Feedback ping-pong pair (phase-11).
        self._feedback_textures: list[moderngl.Texture | None] = [None, None]
        self._feedback_fbos: list[moderngl.Framebuffer | None] = [None, None]
        self._feedback_idx = 0

    def _build_color_fbo(self, size: tuple[int, int]) -> tuple[moderngl.Texture, moderngl.Framebuffer]:
        tex = self.ctx.texture(size, components=4, dtype="f1")
        tex.repeat_x = False
        tex.repeat_y = False
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        fbo = self.ctx.framebuffer(color_attachments=[tex])
        return tex, fbo

    def offscreen_fbo(self, size: tuple[int, int]) -> moderngl.Framebuffer:
        """Return the offscreen FBO, recreating it (and the feedback
        pair) if `size` changed."""
        if size != self._fbo_size or self._fbo is None:
            for t in (self._shader_tex, *self._feedback_textures):
                if t is not None:
                    t.release()
            for f in (self._fbo, *self._feedback_fbos):
                if f is not None:
                    f.release()

            self._shader_tex, self._fbo = self._build_color_fbo(size)
            ft0, ff0 = self._build_color_fbo(size)
            ft1, ff1 = self._build_color_fbo(size)
            self._feedback_textures = [ft0, ft1]
            self._feedback_fbos = [ff0, ff1]
            for fbo in self._feedback_fbos:
                if fbo is not None:
                    fbo.use()
                    self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            self._fbo_size = size
        assert self._fbo is not None
        return self._fbo

    def render(
        self,
        saturation: float = 1.0,
        time_s: float = 0.0,
        glitch: float = 0.0,
        chromatic: float = 0.0,
        kaleidoscope_segments: int = 1,
        trail: float = 0.0,
    ) -> None:
        """Draw the composite to the currently-bound framebuffer."""
        if self._shader_tex is None:
            return  # offscreen_fbo() never called; nothing to composite

        self.ctx.disable(moderngl.BLEND)

        composite_input: moderngl.Texture = self._shader_tex

        if trail > 1e-3:
            target_fbo = self.ctx.fbo

            cur_idx = 1 - self._feedback_idx
            cur_fbo = self._feedback_fbos[cur_idx]
            cur_tex = self._feedback_textures[cur_idx]
            assert cur_fbo is not None and cur_tex is not None
            cur_fbo.use()
            self.ctx.viewport = (0, 0, *self._fbo_size)
            self._shader_tex.use(location=0)
            prev_tex = self._feedback_textures[self._feedback_idx]
            assert prev_tex is not None
            prev_tex.use(location=1)
            _set_uniform(self.feedback_program, "u_trail", float(trail))
            self.feedback_vao.render(moderngl.TRIANGLE_STRIP)

            self._feedback_idx = cur_idx
            composite_input = cur_tex

            target_fbo.use()
            self.ctx.viewport = (0, 0, *self._fbo_size)

        composite_input.use(location=0)
        _set_uniform(self.program, "u_saturation", float(saturation))
        _set_uniform(self.program, "u_glitch", float(glitch))
        _set_uniform(self.program, "u_chromatic", float(chromatic))
        _set_uniform(self.program, "u_kaleidoscope_segments", int(kaleidoscope_segments))
        _set_uniform(self.program, "u_time", float(time_s))

        self.vao.render(moderngl.TRIANGLE_STRIP)


# --------------------------------------------------------------------------- #
# moderngl_window glue
# --------------------------------------------------------------------------- #


class ApopheniaWindow(mglw.WindowConfig):
    """Render window. Particle-only since phase 14.

    Class attributes (`bus`, `state_bus`, `slow_bus`) are set by
    `cli.run` BEFORE `mglw.run_window_config(ApopheniaWindow, args=[])`
    instantiates this. moderngl_window doesn't pass our config through
    __init__, so we bridge via class state.
    """

    title = "apophenia"
    window_size = (1920, 1080)
    aspect_ratio: float | None = None
    samples = 4
    resizable = True
    vsync = True
    cursor = True

    bus: FeatureBus | None = None
    state_bus: StateBus | None = None
    slow_bus: SlowBus | None = None
    fps_log_period_s: float = 5.0

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if ApopheniaWindow.bus is None:
            raise RuntimeError(
                "ApopheniaWindow.bus must be set before mglw.run_window_config"
            )
        from apophenia.visuals.particle_engine import ParticleEngine

        self._bus_ref: FeatureBus = ApopheniaWindow.bus
        self._state_bus_ref: StateBus | None = ApopheniaWindow.state_bus
        self._slow_bus_ref: SlowBus | None = ApopheniaWindow.slow_bus
        # The particle engine is the only renderer of pixel content; the
        # compositor turns its output into the final framebuffer with
        # post-FX. Both require a state bus (for camera + force state).
        self.particle_engine: ParticleEngine | None = (
            ParticleEngine(self.ctx) if ApopheniaWindow.state_bus is not None
            else None
        )
        self.compositor: Compositor | None = (
            Compositor(self.ctx) if self._state_bus_ref is not None else None
        )
        self._frame_count = 0
        self._fps_t0 = time.monotonic()
        self._fps_min = math.inf
        # Freeze caches the last features so a tableau holds across
        # state.transport.freeze=True.
        self._frozen_features: FastFeatures | None = None
        self._frozen_time: float = 0.0
        logger.info(
            "render ready: particle engine%s",
            " + post-FX compositor" if self.compositor is not None else "",
        )

    def on_render(self, time_s: float, frame_time: float) -> None:
        if frame_time > 0:
            self._fps_min = min(self._fps_min, 1.0 / frame_time)

        state = self._state_bus_ref.get() if self._state_bus_ref is not None else None

        if state is not None and state.transport.freeze:
            features = self._frozen_features
            render_time = self._frozen_time
        else:
            features = self._bus_ref.latest()
            render_time = time_s
            self._frozen_features = features
            self._frozen_time = time_s

        if self.compositor is None or self.particle_engine is None:
            # No state → no compositor → nothing to draw. Clear and return.
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            return

        # Particle render → offscreen FBO. The compositor then post-FX's
        # the result onto the screen.
        fbo = self.compositor.offscreen_fbo(self.window_size)
        fbo.use()
        self.ctx.viewport = (0, 0, *self.window_size)
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        slow = self._slow_bus_ref.latest() if self._slow_bus_ref is not None else None
        self.particle_engine.update_and_render(
            features=features,
            time_s=render_time,
            dt=max(frame_time, 1e-3),
            resolution=self.window_size,
            state=state,
            slow=slow,
        )

        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, *self.window_size)

        if state is not None:
            self.compositor.render(
                saturation=state.palette.saturation,
                time_s=time_s,
                glitch=state.fx.glitch,
                chromatic=state.fx.chromatic,
                kaleidoscope_segments=state.fx.kaleidoscope,
                trail=state.fx.trail,
            )
        else:
            self.compositor.render()

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
