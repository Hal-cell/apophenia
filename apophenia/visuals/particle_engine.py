"""3D particle world. Phase-12 addition.

Owns:
  * a ping-pong pair of particle-state VBOs (50k particles by default,
    each particle = 8 floats = 32 bytes, so ~1.6 MB per buffer)
  * a "transform feedback" update program that reads from one VBO and
    writes the next state into the other (no fragment shader; the
    rasterizer is disabled)
  * a render program that draws the *current* VBO as point sprites,
    projecting through an MVP matrix derived from `CameraState`

Architecture choice: we use OpenGL transform feedback (GL 4.1
compatible) rather than compute shaders (GL 4.3+, unavailable on
Apple Silicon's Metal-backed GL). Particle state lives entirely on
the GPU after init; the CPU only uploads ~50 floats of audio uniforms
per frame.

Coordinate system: 14 emitters live on a ring of radius ~1.6 in the
XZ plane around the origin, with slight Y wobble for variation. The
camera looks at the origin from `state.camera.distance` units away,
tilted up by `elevation` degrees, optionally orbiting at
`orbit_speed` revolutions per second.

The engine's `update_and_render(...)` is meant to be called *after*
the 2D shader engine has drawn into the offscreen FBO — particles
render additively on top of the shader output.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import moderngl
import numpy as np

if TYPE_CHECKING:
    from apophenia.audio.features_fast import FastFeatures
    from apophenia.audio.features_slow import SlowFeatures
    from apophenia.state import VisualState

SHADER_DIR = Path(__file__).parent / "shaders"


# --------------------------------------------------------------------------- #
# Matrix helpers (numpy → row-major float32 for moderngl uniform upload)
# --------------------------------------------------------------------------- #


def perspective_matrix(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    """Standard OpenGL perspective projection. Returns a (4, 4) float32
    array in column-major order, suitable for direct upload as a
    `mat4` uniform when moderngl is told the matrix is column-major."""
    f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at_matrix(eye: tuple[float, float, float],
                    target: tuple[float, float, float],
                    up: tuple[float, float, float]) -> np.ndarray:
    """Standard `gluLookAt` view matrix. (4, 4) float32."""
    e = np.array(eye, dtype=np.float32)
    t = np.array(target, dtype=np.float32)
    u = np.array(up, dtype=np.float32)
    f = t - e
    f /= np.linalg.norm(f)
    s = np.cross(f, u)
    s /= np.linalg.norm(s)
    upn = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, 0:3] = s
    m[1, 0:3] = upn
    m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, e)
    m[1, 3] = -np.dot(upn, e)
    m[2, 3] = np.dot(f, e)
    return m


def camera_eye(distance: float, elevation_deg: float, azimuth_rad: float) -> tuple[float, float, float]:
    """Spherical → Cartesian. Camera orbits around (0, 0, 0).
    `azimuth_rad` is the angle in the XZ plane (around Y); 0 looks
    down the +Z axis."""
    elev = math.radians(elevation_deg)
    return (
        distance * math.cos(elev) * math.sin(azimuth_rad),
        distance * math.sin(elev),
        distance * math.cos(elev) * math.cos(azimuth_rad),
    )


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


class ParticleEngine:
    """3D particle simulation + render. See module docstring for context."""

    DEFAULT_N_PARTICLES = 50_000

    def __init__(
        self,
        ctx: moderngl.Context,
        n_particles: int = DEFAULT_N_PARTICLES,
    ) -> None:
        self.ctx = ctx
        self.n_particles = int(n_particles)

        # ---- Programs ---- #
        update_src = (SHADER_DIR / "particle_update.vert").read_text()
        render_vert = (SHADER_DIR / "particle_render.vert").read_text()
        render_frag = (SHADER_DIR / "particle_render.frag").read_text()

        # The update program is a vertex-only program; we declare which
        # `out` varyings get captured into the destination buffer.
        self.update_program = ctx.program(
            vertex_shader=update_src,
            varyings=["v_pos_age", "v_vel_seed"],
        )
        self.render_program = ctx.program(
            vertex_shader=render_vert,
            fragment_shader=render_frag,
        )

        # ---- Particle VBOs (ping-pong pair) ---- #
        # Each particle: vec4 pos_age + vec4 vel_seed = 8 floats = 32 bytes.
        initial = self._initial_particle_data(self.n_particles)
        self._buffers: list[moderngl.Buffer] = [
            ctx.buffer(initial.tobytes()),
            ctx.buffer(reserve=initial.nbytes),
        ]
        self._read_idx = 0  # which buffer holds the current state

        # VAOs for each direction of the ping-pong. The "update" VAO
        # binds to the *read* buffer and feeds out into the write buffer
        # via `vao.transform()`. We rebuild the VAO per frame because
        # the source buffer changes — moderngl's VAO is cheap.
        self._update_vaos = [
            ctx.vertex_array(
                self.update_program,
                [(buf, "4f 4f", "in_pos_age", "in_vel_seed")],
            )
            for buf in self._buffers
        ]
        self._render_vaos = [
            ctx.vertex_array(
                self.render_program,
                [(buf, "4f 4f", "in_pos_age", "in_vel_seed")],
            )
            for buf in self._buffers
        ]

    # ------------------------------------------------------------------ #
    # Init
    # ------------------------------------------------------------------ #

    @staticmethod
    def _initial_particle_data(n: int) -> np.ndarray:
        """Build the starting buffer: every particle is `dead` (age >
        LIFETIME) but assigned a stable channel via `seed`. The first
        few audio frames will respawn them gradually as channels go
        active."""
        rng = np.random.default_rng(seed=42)
        # Layout: (n, 8) row-major float32; columns are
        # [px, py, pz, age, vx, vy, vz, seed].
        data = np.zeros((n, 8), dtype=np.float32)
        # All particles start in the dead pool until audio respawns them.
        data[:, 1] = -100.0  # py = DEAD_POOL.y
        data[:, 3] = 5.0      # age > LIFETIME (4.0)
        data[:, 7] = rng.random(n).astype(np.float32)  # seed ∈ [0, 1)
        return data

    # ------------------------------------------------------------------ #
    # Per-frame
    # ------------------------------------------------------------------ #

    def update_and_render(
        self,
        features: FastFeatures | None,
        time_s: float,
        dt: float,
        resolution: tuple[int, int],
        state: VisualState | None = None,
        slow: SlowFeatures | None = None,
    ) -> None:
        """One simulation step + one render pass.

        `slow` (phase-13) carries the CLAP embedding norm; when None
        (CLAP off / pre-warmup) the audio_norm uniform falls back to 0
        and the flow field still works on RMS / onsets alone.

        Skips silently if `state` is None (no camera state to derive
        an MVP from)."""
        if state is None:
            return

        # ---- Pull audio uniforms (14 floats per array) ---- #
        rms = self._channel_array(features.rms if features else None)
        onset = self._channel_array(features.onset_envelope if features else None)
        centroid = self._channel_array(features.centroid if features else None)
        weight = np.array(state.channel_weight, dtype=np.float32)
        if weight.size != 14:
            weight = np.ones(14, dtype=np.float32)

        # Phase-13 audio energy scalars: a single "loudness" number for
        # flow-field strength, plus the CLAP embedding norm for slow
        # timbre tracking. Multiplied by per-channel weight so a muted
        # channel can't push the overall energy up.
        weighted_rms = rms * weight
        audio_intensity = float(np.clip(weighted_rms.mean() * 1.4, 0.0, 1.0))
        weighted_onset = onset * weight
        onset_avg = float(np.clip(weighted_onset.mean(), 0.0, 1.0))
        audio_norm = float(slow.embedding_norm) if slow is not None else 0.0
        # CLAP norms are typically ~1 (the model L2-normalises); damp to
        # a useful 0..1 range with a soft-knee.
        audio_norm = float(np.clip(audio_norm * 0.5, 0.0, 1.0))

        # ---- Update pass ---- #
        self._upload_update_uniforms(
            dt=dt, time_s=time_s,
            rms=rms, onset=onset, centroid=centroid, weight=weight,
            density=float(state.motion.density),
            speed_scale=float(state.motion.speed),
            onset_gain=float(state.motion.onset_sensitivity)
                       * (1.0 + 0.5 * float(state.mood.arousal)),
            audio_intensity=audio_intensity,
            audio_norm=audio_norm,
            force_noise=float(state.force.noise),
            force_vortex=float(state.force.vortex),
            force_cohesion=float(state.force.cohesion),
            max_speed=float(state.force.max_speed),
        )

        write_idx = 1 - self._read_idx
        # Disable rasterization for the transform pass — we only want
        # the captured varyings, not pixels. moderngl's vao.transform()
        # already implies GL_RASTERIZER_DISCARD; we just call it.
        self._update_vaos[self._read_idx].transform(
            self._buffers[write_idx],
            mode=moderngl.POINTS,
            vertices=self.n_particles,
        )
        self._read_idx = write_idx

        # ---- Render pass ---- #
        # Camera matrix. Phase-13: mood + audio modulate the orbit
        # speed and elevation at runtime — `mood.arousal` boosts orbit
        # rate in proportion to audio_intensity (so the camera "leans
        # into" loud sections), and the per-frame onset average gives
        # a small upward elevation kick (mild camera-shake on hits).
        cam = state.camera
        arousal = float(state.mood.arousal)
        eff_orbit = cam.orbit_speed * (1.0 + 0.6 * arousal * audio_intensity)
        eff_elevation = cam.elevation + onset_avg * 4.0 * max(arousal, 0.0)
        azimuth = (time_s * eff_orbit * 6.2831853) if cam.autorotate else 0.0
        eye = camera_eye(cam.distance, eff_elevation, azimuth)
        view = look_at_matrix(eye, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        aspect = max(resolution[0] / max(resolution[1], 1), 0.01)
        proj = perspective_matrix(cam.fov_deg, aspect, near=0.1, far=50.0)
        mvp = proj @ view  # column-major × column-major

        # Additive blending — bright particles glow brighter where they
        # overlap. Disable depth write so transparent edges don't
        # punch holes; depth test left off for pure additive feel.
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
        self.ctx.disable(moderngl.DEPTH_TEST)

        self._upload_render_uniforms(
            mvp=mvp,
            resolution_y=float(resolution[1]),
            centroid=centroid,
            rms=rms,
            hue_offset_deg=float(state.palette.hue) * 360.0,
            saturation=float(state.palette.saturation),
        )
        # Need PROGRAM_POINT_SIZE so gl_PointSize from the vertex
        # shader takes effect — moderngl exposes this as ctx flag.
        try:
            self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        except Exception:  # noqa: BLE001 — older mglw versions miss the flag
            pass
        self._render_vaos[self._read_idx].render(
            mode=moderngl.POINTS,
            vertices=self.n_particles,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _channel_array(arr: list[float] | None) -> np.ndarray:
        """Pad / truncate a per-channel list to exactly 14 floats."""
        if arr is None or len(arr) == 0:
            return np.zeros(14, dtype=np.float32)
        a = np.array(arr, dtype=np.float32)
        if a.size >= 14:
            return a[:14]
        out = np.zeros(14, dtype=np.float32)
        out[: a.size] = a
        return out

    def _upload_update_uniforms(
        self,
        dt: float,
        time_s: float,
        rms: np.ndarray,
        onset: np.ndarray,
        centroid: np.ndarray,
        weight: np.ndarray,
        density: float,
        speed_scale: float,
        onset_gain: float,
        audio_intensity: float,
        audio_norm: float,
        force_noise: float,
        force_vortex: float,
        force_cohesion: float,
        max_speed: float,
    ) -> None:
        prog = self.update_program
        _set(prog, "u_dt", float(dt))
        _set(prog, "u_time", float(time_s))
        _set(prog, "u_density", density)
        _set(prog, "u_speed_scale", speed_scale)
        _set(prog, "u_onset_gain", onset_gain)
        _set(prog, "u_audio_intensity", float(audio_intensity))
        _set(prog, "u_audio_norm", float(audio_norm))
        # Phase-14 forces.
        _set(prog, "u_force_noise", force_noise)
        _set(prog, "u_force_vortex", force_vortex)
        _set(prog, "u_force_cohesion", force_cohesion)
        _set(prog, "u_max_speed", max_speed)
        # Array uniforms.
        _set_array(prog, "u_rms", rms)
        _set_array(prog, "u_onset", onset)
        _set_array(prog, "u_centroid", centroid)
        _set_array(prog, "u_channel_weight", weight)

    def _upload_render_uniforms(
        self,
        mvp: np.ndarray,
        resolution_y: float,
        centroid: np.ndarray,
        rms: np.ndarray,
        hue_offset_deg: float,
        saturation: float,
    ) -> None:
        prog = self.render_program
        # moderngl accepts mat4 as a flat 16-float tuple. Standard GL is
        # column-major; numpy `@` produces column-major when both
        # operands are column-major, which our `perspective_matrix` and
        # `look_at_matrix` are not — they're row-major. So we flatten
        # in Fortran order (column-major) to match the shader.
        _set(prog, "u_mvp", tuple(mvp.flatten(order="F").tolist()))
        _set(prog, "u_resolution_y", resolution_y)
        _set_array(prog, "u_centroid", centroid)
        _set_array(prog, "u_rms", rms)
        _set(prog, "u_hue_offset_deg", hue_offset_deg)
        _set(prog, "u_saturation", saturation)


# --------------------------------------------------------------------------- #
# Uniform helpers (mirror shader_engine._set_uniform but a touch friendlier)
# --------------------------------------------------------------------------- #


def _set(program: moderngl.Program, name: str, value: object) -> None:
    """Set a uniform if the program declares it; silently ignore otherwise."""
    try:
        u = program[name]
    except KeyError:
        return
    try:
        u.value = value
    except (ValueError, TypeError):
        return


def _set_array(program: moderngl.Program, name: str, arr: np.ndarray) -> None:
    """Set a fixed-size array uniform from a numpy float array."""
    try:
        u = program[name]
    except KeyError:
        return
    try:
        u.write(arr.astype(np.float32).tobytes())
    except (ValueError, TypeError, AttributeError):
        # Fall back to scalar-assignment (older moderngl versions).
        try:
            u.value = tuple(arr.astype(float).tolist())
        except Exception:  # noqa: BLE001
            return
