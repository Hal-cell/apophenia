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
# Emitter pattern math (phase 17)
# --------------------------------------------------------------------------- #


# Number of emitters — must match `N_CHANNELS` in the shader.
N_EMITTERS = 14


def _ring_positions(radius: float) -> np.ndarray:
    """The original phase-12 ring: 14 emitters evenly spaced in the
    XZ plane at the given radius, with slight Y wobble per channel."""
    angles = np.arange(N_EMITTERS, dtype=np.float32) / N_EMITTERS * (2 * np.pi)
    pos = np.zeros((N_EMITTERS, 3), dtype=np.float32)
    pos[:, 0] = np.cos(angles) * radius
    pos[:, 1] = np.sin(np.arange(N_EMITTERS, dtype=np.float32) * 0.91) * 0.25
    pos[:, 2] = np.sin(angles) * radius
    return pos


def _grid_positions(radius: float) -> np.ndarray:
    """7-column × 2-row grid laid horizontally. Whole grid is `radius`
    wide overall."""
    pos = np.zeros((N_EMITTERS, 3), dtype=np.float32)
    for i in range(N_EMITTERS):
        row = i // 7         # 0 or 1
        col = i % 7          # 0..6
        # X spans [-radius, +radius]; Z stays compact.
        pos[i, 0] = (col - 3.0) / 3.0 * radius
        pos[i, 1] = 0.0
        pos[i, 2] = (row - 0.5) * radius * 0.6
    return pos


def _line_positions(radius: float) -> np.ndarray:
    """Single horizontal line along X axis, evenly spaced."""
    pos = np.zeros((N_EMITTERS, 3), dtype=np.float32)
    pos[:, 0] = (np.arange(N_EMITTERS, dtype=np.float32) - 6.5) / 6.5 * radius
    return pos


def _sphere_positions(radius: float) -> np.ndarray:
    """Fibonacci-spiral distribution on a sphere of given radius —
    14 points roughly evenly spread in 3D."""
    pos = np.zeros((N_EMITTERS, 3), dtype=np.float32)
    golden = (1.0 + 5 ** 0.5) / 2.0
    for i in range(N_EMITTERS):
        # Fibonacci: y goes from +1 → -1, theta wraps via golden ratio.
        y = 1.0 - 2.0 * (i + 0.5) / N_EMITTERS
        r_xy = (1.0 - y * y) ** 0.5
        theta = 2 * np.pi * i / golden
        pos[i, 0] = math.cos(theta) * r_xy * radius
        pos[i, 1] = y * radius
        pos[i, 2] = math.sin(theta) * r_xy * radius
    return pos


def _lissajous_positions(radius: float) -> np.ndarray:
    """3D Lissajous curve: 14 emitters sampled evenly along the curve
    `(sin(3t), sin(2t)*0.5, cos(5t))` parameterised in t ∈ [0, 2π]."""
    pos = np.zeros((N_EMITTERS, 3), dtype=np.float32)
    t = np.linspace(0.0, 2 * np.pi, N_EMITTERS, endpoint=False).astype(np.float32)
    pos[:, 0] = np.sin(3 * t) * radius
    pos[:, 1] = np.sin(2 * t) * radius * 0.4
    pos[:, 2] = np.cos(5 * t) * radius
    return pos


_PATTERN_BUILDERS = {
    "ring":      _ring_positions,
    "grid":      _grid_positions,
    "line":      _line_positions,
    "sphere":    _sphere_positions,
    "lissajous": _lissajous_positions,
}


def _pattern_base(pattern: str, radius: float) -> np.ndarray:
    """Look up a pattern builder by name. Unknown patterns fall back
    to `ring` rather than raising — keeps the wire protocol forgiving."""
    builder = _PATTERN_BUILDERS.get(pattern, _ring_positions)
    return builder(radius)


def compute_emitter_positions(
    pattern: str,
    radius: float,
    motion_amp: float,
    motion_speed: float,
    time_s: float,
) -> np.ndarray:
    """Static one-shot emitter math (no morph, no audio). Used by tests
    and as the base for the engine-method version below.

    Returns (14, 3) float32. Each emitter orbits its base position
    on a per-channel Lissajous curve scaled by `motion_amp`.
    """
    base = _pattern_base(pattern, radius)
    if motion_amp > 1e-6:
        t = time_s * motion_speed
        ch = np.arange(N_EMITTERS, dtype=np.float32)
        drift = np.zeros((N_EMITTERS, 3), dtype=np.float32)
        drift[:, 0] = np.sin(t + ch * 0.7) * motion_amp * 0.30
        drift[:, 1] = np.cos(t * 0.8 + ch * 1.3) * motion_amp * 0.15
        drift[:, 2] = np.sin(t * 1.1 + ch * 1.9) * motion_amp * 0.30
        return base + drift
    return base


# Phase-18 dynamic emitter math: smooth pattern morphs + audio-reactive
# motion + per-channel onset pulses. Uses smoothstep over PATTERN_MORPH_S
# seconds to interpolate between the old and new base positions when
# the user changes `state.emitter.pattern`. Lives as a method on
# `ParticleEngine` so it can hold transition state across frames.
PATTERN_MORPH_S = 0.8
ONSET_PULSE_GAIN = 0.18  # how much an emitter pumps outward per onset


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


class ParticleEngine:
    """3D particle simulation + render. See module docstring for context."""

    # Phase-18: bumped from 50k to 100k for denser TD-cluster look.
    # 100k particles × 32 bytes per particle × 2 ping-pong buffers =
    # 6.4 MB GPU memory. Each instanced GL_LINES draw is now 2 verts
    # × 100k instances = 200k vertex shader invocations per frame —
    # well within M3 Max's headroom.
    DEFAULT_N_PARTICLES = 100_000

    def __init__(
        self,
        ctx: moderngl.Context,
        n_particles: int = DEFAULT_N_PARTICLES,
    ) -> None:
        self.ctx = ctx
        self.n_particles = int(n_particles)
        # Phase-18 emitter morph state. We start with the default
        # ring as both prev and target so first frame is static.
        self._emitter_prev_pattern: str = "ring"
        self._emitter_target_pattern: str = "ring"
        self._emitter_target_radius: float = 1.6
        self._emitter_transition_start_t: float = -PATTERN_MORPH_S

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

        # Update-pass VAOs: vertex array reads particle state, transform
        # feedback writes the next state into the other buffer.
        self._update_vaos = [
            ctx.vertex_array(
                self.update_program,
                [(buf, "4f 4f", "in_pos_age", "in_vel_seed")],
            )
            for buf in self._buffers
        ]

        # Render pass: phase-20 billboard ribbon. Each particle is a
        # 4-vertex GL_TRIANGLE_STRIP quad (tail-left, head-left,
        # tail-right, head-right) extruded perpendicular to the view
        # direction by `streak_width`. Replaces the phase-16 2-vertex
        # GL_LINES streak — quads can have arbitrary pixel width while
        # macOS GL caps glLineWidth at 1.
        #
        # Static geometry: 4 (u, v) pairs interleaved as 8 floats.
        # u = head_t (0 = tail, 1 = head); v = side (0 = -width, 1 = +width).
        # Order: tail-left, head-left, tail-right, head-right.
        self._line_geom = ctx.buffer(
            np.array(
                [
                    0.0, 0.0,   # tail, left
                    1.0, 0.0,   # head, left
                    0.0, 1.0,   # tail, right
                    1.0, 1.0,   # head, right
                ],
                dtype="f4",
            ).tobytes()
        )
        self._render_vaos = [
            ctx.vertex_array(
                self.render_program,
                [
                    (self._line_geom, "2f", "in_vertex_uv"),
                    (buf, "4f 4f /i", "in_pos_age", "in_vel_seed"),
                ],
            )
            for buf in self._buffers
        ]

    # ------------------------------------------------------------------ #
    # Init
    # ------------------------------------------------------------------ #

    def _dynamic_emitter_positions(
        self,
        pattern: str,
        radius: float,
        motion_amp: float,
        motion_speed: float,
        time_s: float,
        rms: np.ndarray,
        onset: np.ndarray,
        weight: np.ndarray,
    ) -> np.ndarray:
        """Phase-18/19 dynamic emitter math. On top of
        `compute_emitter_positions`:

        * Pattern morph — when the pattern *string* differs from the
          previously observed target, smoothstep-lerp between the old
          and new base positions over `PATTERN_MORPH_S` seconds.
          Multiple rapid pattern flips interrupt cleanly: the *current*
          interpolated position becomes the new prev. Phase-19 fix:
          only fire morph on pattern-string change, not on radius or
          motion-* drift, so the radius / motion sliders feel
          responsive instead of getting frozen by accidental morph
          interrupts each frame.
        * Radius — applies CONTINUOUSLY. During an in-flight morph, the
          captured prev positions get rescaled by
          `current_radius / capture_radius` so dragging the radius
          slider works seamlessly mid-transition.
        * Per-channel onset pulse — each emitter pushes outward (along
          its base direction from origin) by an amount proportional to
          `rms[ch] + onset[ch]`. Onset transients read as percussive
          emitter pumps.
        """
        # Phase-19: only the pattern *string* triggers a fresh morph.
        # Radius / motion changes are continuous parameters, not
        # transitions — they apply directly through the rest of the
        # math below.
        if pattern != self._emitter_target_pattern:
            # Capture the *current* (interpolated) base as prev. Use the
            # radius at capture time so we can later rescale prev
            # uniformly when the user drags radius mid-morph.
            current_base = self._compute_morphed_base(radius, time_s)
            self._emitter_prev_pattern_positions = current_base.copy()
            self._emitter_prev_capture_radius = radius
            self._emitter_prev_pattern = self._emitter_target_pattern
            self._emitter_target_pattern = pattern
            self._emitter_transition_start_t = time_s

        # Track current radius for telemetry / next pattern transition.
        self._emitter_target_radius = radius

        # Compute base via morph if a transition is in progress.
        base = self._compute_morphed_base(radius, time_s)

        # Drift on top of the morphed base (phase-17 wandering).
        if motion_amp > 1e-6:
            t = time_s * motion_speed
            ch = np.arange(N_EMITTERS, dtype=np.float32)
            drift = np.zeros((N_EMITTERS, 3), dtype=np.float32)
            drift[:, 0] = np.sin(t + ch * 0.7) * motion_amp * 0.30
            drift[:, 1] = np.cos(t * 0.8 + ch * 1.3) * motion_amp * 0.15
            drift[:, 2] = np.sin(t * 1.1 + ch * 1.9) * motion_amp * 0.30
            base = base + drift

        # Per-channel onset pulse: push each emitter outward along its
        # current radial direction by an amount proportional to that
        # channel's audio activity.
        activity = (rms + onset * 1.5) * weight
        # Outward direction = normalised(base) — emitter pumps away
        # from origin, channel-weighted by audio. Avoid div-by-zero
        # for emitters at the origin (e.g. line pattern's middle
        # element).
        norms = np.linalg.norm(base, axis=1, keepdims=True)
        safe_norms = np.maximum(norms, 1e-3)
        outward = base / safe_norms
        pulse = outward * activity[:, np.newaxis] * ONSET_PULSE_GAIN
        base = base + pulse

        return base.astype(np.float32, copy=False)

    def _compute_morphed_base(self, radius: float, time_s: float) -> np.ndarray:
        """Smoothstep-lerp between the morph's prev and target base
        patterns. Returns the (14, 3) base position array. If no morph
        is in progress, returns the target pattern's base directly.

        Phase-19: when prev positions were captured at a different
        radius from the current one, scale them by the radius ratio
        so dragging the radius slider during a morph still updates
        the visual size of both endpoints uniformly. All five
        patterns scale linearly with radius, so this is exact.
        """
        elapsed = time_s - self._emitter_transition_start_t
        if elapsed >= PATTERN_MORPH_S:
            return _pattern_base(self._emitter_target_pattern, radius)
        # Smoothstep weighting.
        t = max(0.0, min(elapsed / PATTERN_MORPH_S, 1.0))
        s = t * t * (3.0 - 2.0 * t)
        prev = getattr(self, "_emitter_prev_pattern_positions", None)
        if prev is None:
            prev = _pattern_base(self._emitter_prev_pattern, radius)
        else:
            # Rescale captured prev to the current radius so the morph
            # tracks slider drags. Y-axis wobble in `_ring_positions`
            # is *not* radius-scaled (it's a fixed `0.25`-amplitude
            # term), so this is a slight approximation for the ring;
            # the visual error is small and the responsiveness gain
            # is worth it.
            capture_r = getattr(self, "_emitter_prev_capture_radius", radius)
            if capture_r > 1e-3 and abs(capture_r - radius) > 1e-4:
                prev = prev * (radius / capture_r)
        target = _pattern_base(self._emitter_target_pattern, radius)
        return prev * (1.0 - s) + target * s

    @staticmethod
    def _initial_particle_data(n: int) -> np.ndarray:
        """Build the starting buffer: every particle is alive and
        scattered in a sphere around its home emitter. Phase-15
        change: no more dead pool; particles are always present in
        the scene from t=0.

        Layout: (n, 8) row-major float32; columns are
        `[px, py, pz, age, vx, vy, vz, seed]`. `seed ∈ [0, 1)` maps
        to a home channel via `int(seed * 14)`. The home channel's
        emitter is at `(cos(angle)*1.6, sin(channel*0.91)*0.25,
        sin(angle)*1.6)` matching the shader's `emitter_pos()`.
        """
        rng = np.random.default_rng(seed=42)
        data = np.zeros((n, 8), dtype=np.float32)

        seeds = rng.random(n).astype(np.float32)
        channels = np.clip(np.floor(seeds * 14).astype(int), 0, 13)
        angles = channels.astype(np.float32) / 14.0 * (2 * np.pi)

        # Emitter ring positions (must match `emitter_pos()` in the
        # update shader exactly).
        ex = np.cos(angles) * 1.6
        ez = np.sin(angles) * 1.6
        ey = np.sin(channels.astype(np.float32) * 0.91) * 0.25

        # Random offset in a sphere of radius ~0.9 around each emitter
        # so particles start visibly distributed rather than piled up.
        rand_xyz = (rng.random((n, 3)).astype(np.float32) - 0.5) * 1.8
        # Squash Y a bit so the cluster is more disc-shaped than spherical
        # — emitters live on the XZ ring so vertical spread should be
        # subtler than radial spread.
        rand_xyz[:, 1] *= 0.4

        data[:, 0] = ex + rand_xyz[:, 0]
        data[:, 1] = ey + rand_xyz[:, 1]
        data[:, 2] = ez + rand_xyz[:, 2]
        data[:, 3] = 0.0  # age — meaningless under phase-15 persistence

        # Tiny random initial velocity so the first frames have a touch
        # of motion before forces kick in.
        rand_vel = (rng.random((n, 3)).astype(np.float32) - 0.5) * 0.3
        data[:, 4] = rand_vel[:, 0]
        data[:, 5] = rand_vel[:, 1] * 0.5
        data[:, 6] = rand_vel[:, 2]
        data[:, 7] = seeds
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

        # Phase-17/18: compute live emitter positions from EmitterState
        # + audio activity + transition state. Includes:
        #   - smooth morph between previous and new patterns when the
        #     user changes `state.emitter.pattern`
        #   - audio-reactive wobble: motion_amp scales with mood.arousal
        #     × audio_intensity (loud arousal-positive mixes wobble more)
        #   - per-channel onset pulse: each emitter pumps outward on its
        #     channel's transient
        # Uploaded as a `vec3 u_emitters[14]` uniform array.
        arousal = float(state.mood.arousal)
        effective_motion_amp = float(state.emitter.motion_amp) * (
            1.0 + 0.6 * max(arousal, 0.0) * audio_intensity
        )
        emitters = self._dynamic_emitter_positions(
            pattern=state.emitter.pattern,
            radius=float(state.emitter.radius),
            motion_amp=effective_motion_amp,
            motion_speed=float(state.emitter.motion_speed),
            time_s=time_s,
            rms=rms,
            onset=onset,
            weight=weight,
        )

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
            emitter_positions=emitters,
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
            streak_length=float(state.force.streak_length),
            streak_width=float(state.force.streak_width),
            camera_pos=eye,
        )
        # Phase-20: instanced GL_TRIANGLE_STRIP ribbon. Each particle is
        # one 4-vertex billboard quad. The static quad geom (4 (u, v)
        # pairs) is consumed by the vertex shader four times per
        # particle; the per-instance attributes are shared across all
        # four corners. Triangle strip with 4 verts = 2 triangles =
        # 1 quad.
        self._render_vaos[self._read_idx].render(
            mode=moderngl.TRIANGLE_STRIP,
            vertices=4,
            instances=self.n_particles,
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
        emitter_positions: np.ndarray,
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
        # Phase-17: emitter positions packed flat (14 × 3 = 42 floats).
        _set_array(prog, "u_emitters", emitter_positions.reshape(-1))

    def _upload_render_uniforms(
        self,
        mvp: np.ndarray,
        resolution_y: float,
        centroid: np.ndarray,
        rms: np.ndarray,
        hue_offset_deg: float,
        saturation: float,
        streak_length: float,
        streak_width: float,
        camera_pos: tuple[float, float, float],
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
        _set(prog, "u_streak_length", streak_length)
        # Phase-20 ribbon uniforms.
        _set(prog, "u_streak_width", streak_width)
        _set(prog, "u_camera_pos", tuple(float(c) for c in camera_pos))


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
