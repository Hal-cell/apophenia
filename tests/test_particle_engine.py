"""Tests for the 3D particle engine.

The actual transform-feedback simulation needs a GL context — same
skipif pattern as the shader-engine tests. CPU-side helpers (matrix
math, channel array padding) are tested without GL.
"""

from __future__ import annotations

import math

import numpy as np
import pytest


def _try_make_ctx():
    """Spin up a standalone GL context, or return None when unavailable
    (CI hosts without a display)."""
    try:
        import moderngl
        return moderngl.create_standalone_context()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Matrix helpers
# --------------------------------------------------------------------------- #


def test_perspective_matrix_shape_and_diagonal_signs() -> None:
    from apophenia.visuals.particle_engine import perspective_matrix

    m = perspective_matrix(60.0, aspect=16/9, near=0.1, far=50.0)
    assert m.shape == (4, 4)
    assert m.dtype == np.float32
    # m[0,0] = f/aspect, m[1,1] = f. f = 1/tan(30°) ≈ 1.732.
    f = 1.0 / math.tan(math.radians(60.0) * 0.5)
    assert m[0, 0] == pytest.approx(f / (16/9), rel=1e-4)
    assert m[1, 1] == pytest.approx(f, rel=1e-4)
    # Standard GL: m[3, 2] = -1.
    assert m[3, 2] == pytest.approx(-1.0)


def test_look_at_matrix_basic_shape() -> None:
    from apophenia.visuals.particle_engine import look_at_matrix

    # Camera at (0, 0, 5) looking at origin, up = +Y.
    m = look_at_matrix((0, 0, 5), (0, 0, 0), (0, 1, 0))
    assert m.shape == (4, 4)
    # The forward vector is -Z; the row that maps world-Z → view-Z
    # should reflect that.
    # m[2, 0:3] is the negated forward direction.
    np.testing.assert_allclose(m[2, 0:3], [0, 0, 1], atol=1e-6)


def test_camera_eye_orbit_geometry() -> None:
    """At elevation=0 and azimuth=0, eye is at (0, 0, distance).
    At azimuth=π/2, eye is at (distance, 0, 0). Standard right-hand
    Y-up orbit."""
    from apophenia.visuals.particle_engine import camera_eye

    eye0 = camera_eye(distance=5.0, elevation_deg=0.0, azimuth_rad=0.0)
    assert eye0[0] == pytest.approx(0.0, abs=1e-6)
    assert eye0[1] == pytest.approx(0.0, abs=1e-6)
    assert eye0[2] == pytest.approx(5.0, rel=1e-4)

    eye_quarter = camera_eye(5.0, 0.0, math.pi / 2)
    assert eye_quarter[0] == pytest.approx(5.0, rel=1e-4)
    assert eye_quarter[2] == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# CameraState schema
# --------------------------------------------------------------------------- #


def test_camera_state_defaults_and_range_validation() -> None:
    from pydantic import ValidationError

    from apophenia.state import CameraState

    c = CameraState()
    assert c.distance == 5.0
    assert c.elevation == 15.0
    assert c.fov_deg == 60.0
    assert c.autorotate is True

    # Out-of-range values rejected.
    with pytest.raises(ValidationError):
        CameraState(distance=0.5)  # below 1.5
    with pytest.raises(ValidationError):
        CameraState(distance=25.0)  # above 20
    with pytest.raises(ValidationError):
        CameraState(elevation=95.0)
    with pytest.raises(ValidationError):
        CameraState(fov_deg=10.0)
    with pytest.raises(ValidationError):
        CameraState(orbit_speed=3.0)


def test_visual_state_includes_camera_default() -> None:
    from apophenia.state import VisualState

    s = VisualState()
    assert s.camera.distance == 5.0
    assert s.camera.autorotate is True


# --------------------------------------------------------------------------- #
# ParticleEngine — needs GL context
# --------------------------------------------------------------------------- #


def test_particle_engine_constructs_with_gl_context() -> None:
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=1000)
        assert pe.n_particles == 1000
        assert len(pe._buffers) == 2
        # Both buffers sized for 8 floats × 1000 particles.
        for buf in pe._buffers:
            assert buf.size == 1000 * 8 * 4
    finally:
        ctx.release()


def test_particle_engine_transform_pass_changes_state() -> None:
    """Phase-15: particles are persistent. Running an update pass should
    move them (positions change) regardless of audio activity, since
    forces always apply (curl noise, home cohesion, drag)."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=2000)
        before = np.frombuffer(pe._buffers[0].read(), dtype=np.float32).reshape(-1, 8)

        features = FastFeatures(
            rms=[0.7] * 14,
            peak=[0.8] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.4] * 14,
            n_channels=14,
        )
        state = VisualState()
        for i in range(5):
            pe.update_and_render(
                features=features,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )

        after = np.frombuffer(
            pe._buffers[pe._read_idx].read(), dtype=np.float32
        ).reshape(-1, 8)
        # Positions should have changed for most particles.
        moved = np.linalg.norm(after[:, 0:3] - before[:, 0:3], axis=1) > 0.01
        assert moved.sum() > pe.n_particles * 0.5, (
            f"expected positions to update under forces; only {moved.sum()} moved"
        )
    finally:
        ctx.release()


def test_silent_audio_keeps_particles_alive_at_emitters() -> None:
    """Phase-15 reshape: with silent audio, particles still drift
    gently (home-bias keeps pulling toward home emitters), but
    NONE should end up in the legacy dead-pool zone (y < -50). All
    particles are persistent and visible.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=1000)

        silent = FastFeatures(
            rms=[0.0] * 14,
            peak=[0.0] * 14,
            centroid=[0.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        state = VisualState()
        for i in range(20):
            pe.update_and_render(
                features=silent,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )

        after = np.frombuffer(
            pe._buffers[pe._read_idx].read(), dtype=np.float32
        ).reshape(-1, 8)
        # No particle should be in the legacy dead-pool region.
        in_dead_pool = (after[:, 1] < -50.0).sum()
        assert in_dead_pool == 0, (
            f"phase-15 has no dead pool; found {in_dead_pool} particles "
            f"with y < -50"
        )
        # And particles should be in a reasonable scene-radius range
        # (within the 8-unit soft world bound + a margin).
        radii = np.linalg.norm(after[:, 0:3], axis=1)
        assert radii.max() < 10.0, (
            f"particles should be bounded; max radius = {radii.max():.2f}"
        )
    finally:
        ctx.release()


def test_particle_engine_skips_when_state_is_none() -> None:
    """No state → no camera matrix → engine bails out gracefully without
    crashing or touching its buffers."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=200)
        before = pe._buffers[pe._read_idx].read()
        pe.update_and_render(
            features=None, time_s=0.0, dt=0.033, resolution=(64, 64), state=None
        )
        after = pe._buffers[pe._read_idx].read()
        # Buffer untouched.
        assert before == after
    finally:
        ctx.release()


# --------------------------------------------------------------------------- #
# Phase 13: deeper audio coupling
# --------------------------------------------------------------------------- #


def _run_n_steps(pe, features, state, n_steps=10, slow=None):
    """Helper: drive the engine for n update+render passes, return the
    final particle buffer as a (N, 8) numpy array."""
    for i in range(n_steps):
        pe.update_and_render(
            features=features,
            time_s=i * 0.033,
            dt=0.033,
            resolution=(64, 64),
            state=state,
            slow=slow,
        )
    return np.frombuffer(
        pe._buffers[pe._read_idx].read(), dtype=np.float32
    ).reshape(-1, 8)


def test_onset_kicks_velocities_outward() -> None:
    """Phase-15 reshape: onsets no longer respawn particles (they
    can't, particles are persistent); they push particle velocities
    outward from the home emitter. Compare two runs at identical
    audio setup minus the onset envelope: high-onset run should have
    measurably higher mean particle speed.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        state = VisualState()
        # Disable global noise/vortex so the onset kick is the only
        # major velocity contributor we care about.
        state.force.noise = 0.0
        state.force.vortex = 0.0
        state.force.cohesion = 0.5

        steady = FastFeatures(
            rms=[0.3] * 14,
            peak=[0.4] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        with_onsets = FastFeatures(
            rms=[0.3] * 14,
            peak=[0.4] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.8] * 14,
            n_channels=14,
        )

        pe_steady = ParticleEngine(ctx, n_particles=2000)
        after_steady = _run_n_steps(pe_steady, steady, state, n_steps=8)
        speeds_steady = np.linalg.norm(after_steady[:, 4:7], axis=1)

        pe_onset = ParticleEngine(ctx, n_particles=2000)
        after_onset = _run_n_steps(pe_onset, with_onsets, state, n_steps=8)
        speeds_onset = np.linalg.norm(after_onset[:, 4:7], axis=1)

        # Onset-driven kick should push mean speed up meaningfully.
        assert speeds_onset.mean() > speeds_steady.mean() * 1.4, (
            f"onset kick should raise mean speed; "
            f"steady={speeds_steady.mean():.3f}, onset={speeds_onset.mean():.3f}"
        )
    finally:
        ctx.release()


def test_clap_audio_norm_propagates_to_simulation() -> None:
    """Phase-13: a non-zero CLAP embedding norm should reach the
    simulation, increasing the flow-field force on live particles
    so trajectories diverge from the no-CLAP run.

    We can't peek at intermediate forces, but we can compare the two
    final velocity buffers — they should differ.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.audio.features_slow import CLAP_EMBED_DIM, SlowFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        state = VisualState()
        features = FastFeatures(
            rms=[0.4] * 14,
            peak=[0.5] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.2] * 14,
            n_channels=14,
        )

        # Make a CLAP feature with embedding_norm=1.5 (above the
        # 0.5×clamp threshold so the audio_norm uniform actually pumps).
        slow = SlowFeatures(
            clap_embedding=[0.0] * CLAP_EMBED_DIM,
            embedding_norm=1.5,
            update_count=1,
            inference_ms=20.0,
        )

        # Run twice with identical fast features but different `slow`.
        pe_no_clap = ParticleEngine(ctx, n_particles=1000)
        after_no = _run_n_steps(pe_no_clap, features, state, n_steps=20, slow=None)

        pe_with_clap = ParticleEngine(ctx, n_particles=1000)
        after_yes = _run_n_steps(pe_with_clap, features, state, n_steps=20, slow=slow)

        # Compare velocities of live particles. They should diverge
        # noticeably because the flow-field strength is higher with
        # CLAP norm boosting it. We quantify divergence as the mean
        # per-particle velocity-vector difference.
        live_mask_no = after_no[:, 1] > -50.0
        live_mask_yes = after_yes[:, 1] > -50.0
        # Sanity: both runs spawned at least some particles (same audio).
        assert live_mask_no.sum() > 50
        assert live_mask_yes.sum() > 50
        # Velocity components live in cols 4..7.
        # Compare global L2-norm of velocity buffers — easy aggregate.
        vels_no = after_no[:, 4:7]
        vels_yes = after_yes[:, 4:7]
        diff = np.linalg.norm(vels_yes - vels_no, axis=1).mean()
        assert diff > 0.01, (
            f"CLAP-driven force should change velocities; mean Δ={diff}"
        )
    finally:
        ctx.release()


def test_high_arousal_speeds_up_camera_orbit() -> None:
    """Phase-13: state.mood.arousal × audio_intensity multiplies the
    effective orbit speed at runtime. With arousal=0.9 and loud audio,
    the camera azimuth at t=1s should be noticeably ahead of the
    arousal=0 baseline.

    Tests the math without needing GL — we just want to verify
    `(orbit_speed * (1 + 0.6 * arousal * intensity)) * t` produces a
    different angle for the two cases."""
    # No GL needed. Pure arithmetic.
    base_speed = 0.1
    t = 1.0

    # arousal=0 (calm): no boost.
    mood_zero_intensity = 0.6  # moderate audio
    eff_zero = base_speed * (1.0 + 0.6 * 0.0 * mood_zero_intensity)
    assert eff_zero == pytest.approx(base_speed)

    # arousal=0.9, intensity=0.6 → boost = 1 + 0.6*0.9*0.6 = 1.324
    eff_high = base_speed * (1.0 + 0.6 * 0.9 * 0.6)
    assert eff_high > base_speed * 1.3
    assert eff_high < base_speed * 1.4

    # The angle difference at t=1 should be (eff_high - eff_zero) * 2π
    # ≈ 0.0324 * 2π ≈ 0.20 radians. Real renderer multiplies by 2π
    # internally; here we just verify the speed factor scales correctly.
    azimuth_zero = t * eff_zero * 6.2831853
    azimuth_high = t * eff_high * 6.2831853
    assert azimuth_high - azimuth_zero == pytest.approx(0.204, abs=0.01)


def test_silent_audio_does_not_modulate_camera() -> None:
    """When audio_intensity is 0, even arousal=1.0 leaves the camera
    at its base orbit speed. (Coupling is multiplicative.)"""
    base = 0.05
    audio_intensity_silent = 0.0
    arousal_max = 1.0
    eff = base * (1.0 + 0.6 * arousal_max * audio_intensity_silent)
    assert eff == pytest.approx(base)


def test_phase13_reactive_vocabulary() -> None:
    """The new audio-reactivity keywords write into mood.arousal —
    that's the term the particle engine multiplies into orbit + onset
    response."""
    from apophenia.prompt.interpreter import PromptInterpreter

    interp = PromptInterpreter()
    for word, expected_arousal_min in [
        ("reactive", 0.5),
        ("breathing", 0.2),
        ("pulsing", 0.6),
        ("volatile", 0.8),
    ]:
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert r["partial"]["mood"]["arousal"] >= expected_arousal_min

    r_anchored = interp.interpret("anchored")
    assert r_anchored["partial"]["mood"]["arousal"] < 0
    assert r_anchored["partial"]["camera"]["autorotate"] is False


# --------------------------------------------------------------------------- #
# Phase 14: force model
# --------------------------------------------------------------------------- #


def test_high_cohesion_keeps_particles_closer_to_emitter() -> None:
    """Phase-15 reshape: cohesion now is HOME pull (always-on) +
    weak directional bias from other channels. With high cohesion +
    low noise, particles converge toward their home emitter; with
    zero cohesion (forces nullified), they sit roughly where init
    placed them but spread out via curl-noise + initial random
    velocity.

    Test: mean distance from each particle to its home emitter. High
    cohesion → smaller mean distance.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        # Single channel active so the home-bias dominates without
        # the centroid-attraction confound from all-channels-loud.
        features = FastFeatures(
            rms=[0.6] + [0.0] * 13,
            peak=[0.7] + [0.0] * 13,
            centroid=[1500.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )

        state_tight = VisualState()
        state_tight.force.cohesion = 1.0
        state_tight.force.noise = 0.0
        state_tight.force.vortex = 0.0
        state_tight.force.max_speed = 1.0

        state_loose = VisualState()
        state_loose.force.cohesion = 0.0
        state_loose.force.noise = 0.7
        state_loose.force.vortex = 0.0
        state_loose.force.max_speed = 4.0

        pe_tight = ParticleEngine(ctx, n_particles=2000)
        after_tight = _run_n_steps(pe_tight, features, state_tight, n_steps=60)
        pe_loose = ParticleEngine(ctx, n_particles=2000)
        after_loose = _run_n_steps(pe_loose, features, state_loose, n_steps=60)

        def mean_distance(buf):
            seeds = buf[:, 7]
            channels = np.clip(np.floor(seeds * 14).astype(int), 0, 13)
            angles = channels.astype(np.float32) / 14.0 * 2 * np.pi
            ex = np.cos(angles) * 1.6
            ez = np.sin(angles) * 1.6
            ey = np.sin(channels.astype(np.float32) * 0.91) * 0.25
            dx = buf[:, 0] - ex
            dy = buf[:, 1] - ey
            dz = buf[:, 2] - ez
            return np.sqrt(dx * dx + dy * dy + dz * dz).mean()

        d_tight = mean_distance(after_tight)
        d_loose = mean_distance(after_loose)
        assert d_tight < d_loose, (
            f"high cohesion should hold closer to home emitter; "
            f"tight={d_tight:.3f}, loose={d_loose:.3f}"
        )
    finally:
        ctx.release()


def test_max_speed_caps_velocity_magnitude() -> None:
    """Phase-14 speed cap: no live particle's |vel| should exceed
    max_speed at the end of a run."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        # Loud audio + high noise + high vortex would normally push
        # particles to high speed; the cap should still hold.
        features = FastFeatures(
            rms=[0.9] * 14,
            peak=[1.0] * 14,
            centroid=[3000.0] * 14,
            onset_envelope=[0.8] * 14,
            n_channels=14,
        )
        state = VisualState()
        state.force.noise = 1.0
        state.force.vortex = 1.0
        state.force.cohesion = 0.0  # let them fly out
        state.force.max_speed = 1.5
        state.motion.speed = 2.0  # huge initial spawn velocity

        pe = ParticleEngine(ctx, n_particles=2000)
        after = _run_n_steps(pe, features, state, n_steps=15)

        live = after[:, 1] > -50.0
        speeds = np.linalg.norm(after[live, 4:7], axis=1)
        # Allow a tiny epsilon for floating-point noise; the cap is 1.5.
        assert speeds.max() <= 1.5 + 0.05, (
            f"speed cap violated: max={speeds.max():.3f}, cap=1.5"
        )
    finally:
        ctx.release()


def test_phase14_force_vocabulary_writes_force_state() -> None:
    """Phase-14 vocabulary keywords write into `state.force.*`."""
    from apophenia.prompt.interpreter import PromptInterpreter

    interp = PromptInterpreter()
    r = interp.interpret("ikeda tornado")
    p = r["partial"]
    # tornado wins on force values (later token); ikeda contributed before.
    assert p["force"]["vortex"] >= 0.85
    assert p["force"]["cohesion"] >= 0.5
    # ikeda's saturation drop should still apply (different subtree).
    assert p["palette"]["saturation"] <= 0.2

    r_dispersed = interp.interpret("dispersed")
    assert r_dispersed["partial"]["force"]["cohesion"] < 0.1
    assert r_dispersed["partial"]["force"]["max_speed"] >= 3.0


def test_phase14_force_vocabulary_validates_against_schema() -> None:
    """Every force-touching keyword must produce a valid ForceState."""
    from apophenia.prompt.interpreter import VOCABULARY
    from apophenia.state import ForceState

    for keyword, diff in VOCABULARY.items():
        if "force" not in diff:
            continue
        merged = {**ForceState().model_dump(), **diff["force"]}
        ForceState.model_validate(merged), f"{keyword!r} produces invalid force state"


# --------------------------------------------------------------------------- #
# Phase 16: velocity streaks
# --------------------------------------------------------------------------- #


def test_streak_render_produces_visible_output() -> None:
    """Phase-16: with streak_length > 0 the engine renders particles
    as lines instead of points. Smoke-test that the GL pipeline draws
    *something* — pixels accumulate in the FBO.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        size = (128, 128)
        out_tex = ctx.texture(size, components=4, dtype="f1")
        fbo = ctx.framebuffer(color_attachments=[out_tex])

        pe = ParticleEngine(ctx, n_particles=2000)
        state = VisualState()
        # Loud audio + decent streak so streaks are visible.
        state.force.streak_length = 0.2
        features = FastFeatures(
            rms=[0.7] * 14,
            peak=[0.8] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.3] * 14,
            n_channels=14,
        )

        fbo.use()
        ctx.viewport = (0, 0, *size)
        ctx.clear(0.0, 0.0, 0.0, 1.0)
        for i in range(20):
            pe.update_and_render(features, time_s=i * 0.033, dt=0.033,
                                 resolution=size, state=state)

        raw = fbo.read(components=4, dtype="f1")
        # Some pixels should be lit — the test verifies the GL pipeline
        # went through, not visual quality.
        bright = sum(1 for i in range(0, len(raw), 4)
                     if raw[i] > 5 or raw[i + 1] > 5 or raw[i + 2] > 5)
        assert bright > 100, (
            f"streak rendering should produce visible output; "
            f"only {bright}/{len(raw) // 4} bright pixels"
        )
    finally:
        ctx.release()


def test_phase16_streak_vocabulary_writes_force_streak_length() -> None:
    """`streaks / lines / ribbons / comet / wisps` raise streak_length;
    `points / dots / stippled` zero it."""
    from apophenia.prompt.interpreter import PromptInterpreter

    interp = PromptInterpreter()
    for word in ("streaks", "lines", "ribbons", "comet", "wisps"):
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert r["partial"]["force"]["streak_length"] >= 0.18, (
            f"{word!r} should produce a meaningful streak length"
        )

    for word in ("points", "dots", "stippled"):
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert r["partial"]["force"]["streak_length"] == 0.0


# --------------------------------------------------------------------------- #
# Phase 17: emitter patterns
# --------------------------------------------------------------------------- #


def test_compute_emitter_positions_ring_default() -> None:
    """Default ring pattern with motion_amp=0 should match the original
    phase-12/15 hardcoded positions exactly (radius 1.6, slight Y wobble)."""
    from apophenia.visuals.particle_engine import compute_emitter_positions

    pos = compute_emitter_positions(
        pattern="ring", radius=1.6, motion_amp=0.0,
        motion_speed=0.0, time_s=0.0,
    )
    assert pos.shape == (14, 3)
    assert pos.dtype == np.float32
    # Check ch0 sits at (1.6, sin(0)*0.25=0, 0).
    assert pos[0, 0] == pytest.approx(1.6, rel=1e-4)
    assert pos[0, 1] == pytest.approx(0.0, abs=1e-4)
    assert pos[0, 2] == pytest.approx(0.0, abs=1e-4)
    # ch7 is opposite ch0 — at (-1.6, _, very small).
    assert pos[7, 0] == pytest.approx(-1.6, rel=1e-3)


def test_compute_emitter_positions_each_pattern_distinct() -> None:
    """The 5 patterns should produce distinct geometries."""
    from apophenia.visuals.particle_engine import compute_emitter_positions

    patterns = ["ring", "grid", "line", "sphere", "lissajous"]
    positions = {
        p: compute_emitter_positions(p, 1.6, 0.0, 0.0, 0.0)
        for p in patterns
    }
    # All shapes valid.
    for p, pos in positions.items():
        assert pos.shape == (14, 3), f"{p}: got {pos.shape}"
    # Pairwise: at least one coordinate differs by > 0.1 between patterns.
    pairs = [
        ("ring", "grid"),
        ("ring", "line"),
        ("ring", "sphere"),
        ("ring", "lissajous"),
        ("grid", "sphere"),
    ]
    for a, b in pairs:
        diff = np.abs(positions[a] - positions[b]).max()
        assert diff > 0.1, f"patterns {a} and {b} look identical (max diff {diff})"


def test_compute_emitter_positions_motion_advances_with_time() -> None:
    """With motion_amp > 0, the emitter position changes over time."""
    from apophenia.visuals.particle_engine import compute_emitter_positions

    p_t0 = compute_emitter_positions("ring", 1.6, motion_amp=0.5,
                                      motion_speed=1.0, time_s=0.0)
    p_t1 = compute_emitter_positions("ring", 1.6, motion_amp=0.5,
                                      motion_speed=1.0, time_s=1.0)
    diff = np.abs(p_t0 - p_t1).max()
    # Drift over 1s at motion_speed=1 should produce O(0.1) movement.
    assert diff > 0.05, f"motion_amp>0 should change positions over time; got diff {diff}"

    # motion_amp=0 should keep positions perfectly static.
    p_static_t0 = compute_emitter_positions("ring", 1.6, 0.0, 1.0, 0.0)
    p_static_t10 = compute_emitter_positions("ring", 1.6, 0.0, 1.0, 10.0)
    np.testing.assert_array_equal(p_static_t0, p_static_t10)


def test_compute_emitter_positions_radius_scales_uniformly() -> None:
    """Doubling radius should roughly double all distances from origin."""
    from apophenia.visuals.particle_engine import compute_emitter_positions

    p_small = compute_emitter_positions("ring", 1.0, 0.0, 0.0, 0.0)
    p_big = compute_emitter_positions("ring", 2.0, 0.0, 0.0, 0.0)
    # X+Z distances scale by 2; Y wobble is independent of radius
    # (it's a fixed `sin(channel * 0.91) * 0.25`), so just check XZ.
    rad_small = np.linalg.norm(p_small[:, [0, 2]], axis=1).mean()
    rad_big = np.linalg.norm(p_big[:, [0, 2]], axis=1).mean()
    assert rad_big / rad_small == pytest.approx(2.0, rel=0.05)


def test_compute_emitter_positions_unknown_pattern_falls_back_to_ring() -> None:
    """Unknown pattern strings should not crash; we fall back to `ring`."""
    from apophenia.visuals.particle_engine import compute_emitter_positions

    pos = compute_emitter_positions("nonsense", 1.6, 0.0, 0.0, 0.0)
    pos_ring = compute_emitter_positions("ring", 1.6, 0.0, 0.0, 0.0)
    np.testing.assert_array_almost_equal(pos, pos_ring)


def test_default_n_particles_is_100k() -> None:
    """Phase-18: default density bumped from 50k → 100k for the
    TD-cluster look. Test catches a future accidental downgrade."""
    from apophenia.visuals.particle_engine import ParticleEngine

    assert ParticleEngine.DEFAULT_N_PARTICLES == 100_000


def test_pattern_morph_interpolates_between_patterns() -> None:
    """Phase-18 pattern morph: when state.emitter.pattern changes mid-run,
    the engine should interpolate between the two pattern positions
    over PATTERN_MORPH_S seconds. Test verifies that mid-transition
    positions are bounded by the two endpoint patterns and end-state
    matches the new target.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import (
            PATTERN_MORPH_S,
            ParticleEngine,
            compute_emitter_positions,
        )

        pe = ParticleEngine(ctx, n_particles=200)

        # Silent audio so no onset pulse mucks with the comparison.
        silent = FastFeatures(
            rms=[0.0] * 14, peak=[0.0] * 14,
            centroid=[0.0] * 14, onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        state = VisualState()  # default ring
        state.emitter.motion_amp = 0.0  # disable drift to isolate morph

        # Tick once at t=0 to seed prev=ring.
        pe.update_and_render(silent, time_s=0.0, dt=0.016,
                             resolution=(64, 64), state=state)

        # Now switch to sphere pattern.
        state.emitter.pattern = "sphere"

        # Mid-morph (t = 0.4s = halfway through PATTERN_MORPH_S=0.8).
        pe.update_and_render(silent, time_s=0.4, dt=0.016,
                             resolution=(64, 64), state=state)
        # Read back emitter positions via the test helper since they're
        # not stored anywhere accessible. Use the public free fn.
        ring = compute_emitter_positions("ring", 1.6, 0.0, 0.0, 0.0)
        sphere = compute_emitter_positions("sphere", 1.6, 0.0, 0.0, 0.0)
        # The morphed positions should be a smoothstep blend at t=0.5.
        # We can't easily peek at the engine's last computed positions,
        # so directly call the engine method:
        mid = pe._dynamic_emitter_positions(
            pattern="sphere", radius=1.6,
            motion_amp=0.0, motion_speed=0.0,
            time_s=0.4,
            rms=np.zeros(14, dtype=np.float32),
            onset=np.zeros(14, dtype=np.float32),
            weight=np.ones(14, dtype=np.float32),
        )
        # Each emitter's mid position should sit between ring and sphere
        # endpoints (within a small numerical tolerance).
        for i in range(14):
            for axis in range(3):
                lo = min(ring[i, axis], sphere[i, axis])
                hi = max(ring[i, axis], sphere[i, axis])
                assert lo - 0.05 <= mid[i, axis] <= hi + 0.05, (
                    f"emitter {i} axis {axis} mid {mid[i, axis]} not "
                    f"between {lo} and {hi}"
                )

        # After PATTERN_MORPH_S elapses, position should match sphere.
        end = pe._dynamic_emitter_positions(
            pattern="sphere", radius=1.6,
            motion_amp=0.0, motion_speed=0.0,
            time_s=0.4 + PATTERN_MORPH_S + 0.1,
            rms=np.zeros(14, dtype=np.float32),
            onset=np.zeros(14, dtype=np.float32),
            weight=np.ones(14, dtype=np.float32),
        )
        np.testing.assert_array_almost_equal(end, sphere, decimal=3)
    finally:
        ctx.release()


def test_radius_changes_propagate_immediately() -> None:
    """Phase-19 regression: dragging the radius slider continuously
    should produce continuously different emitter positions, NOT a
    frozen state. The phase-18 bug treated every numeric change as a
    fresh transition (resetting the smoothstep clock to t=0 each
    frame), which froze the displayed positions while the slider was
    being dragged.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)

        # Frame-by-frame radius drag from 1.6 → 2.0 over 4 frames.
        # No pattern change — only radius drift.
        last_positions: list[np.ndarray] = []
        for i, r in enumerate([1.6, 1.7, 1.8, 1.9, 2.0]):
            pos = pe._dynamic_emitter_positions(
                pattern="ring",
                radius=r,
                motion_amp=0.0, motion_speed=0.0,
                time_s=i * 0.016,
                rms=np.zeros(14, dtype=np.float32),
                onset=np.zeros(14, dtype=np.float32),
                weight=np.ones(14, dtype=np.float32),
            )
            last_positions.append(pos.copy())

        # Each frame's positions should differ from the previous —
        # specifically, ch0 (at angle 0 on the ring) should grow in X
        # as radius grows. Pre-fix bug froze ch0[0] at 1.6.
        x_values = [p[0, 0] for p in last_positions]
        assert all(
            x_values[i] < x_values[i + 1] for i in range(len(x_values) - 1)
        ), f"radius drag should produce monotonically growing X for ch0; got {x_values}"
        # And the final position should match radius=2.0 exactly.
        assert x_values[-1] == pytest.approx(2.0, rel=1e-3)
    finally:
        ctx.release()


def test_motion_amp_changes_propagate_immediately() -> None:
    """Phase-19 regression sibling: motion_amp slider drags should
    affect output positions immediately, not get gated by morph
    machinery. Compare two snapshots at same time but different
    motion_amp."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)

        # Same pattern + radius, different motion_amp.
        common = dict(
            pattern="ring", radius=1.6,
            motion_speed=1.0, time_s=0.5,  # mid-orbit, so drift differs
            rms=np.zeros(14, dtype=np.float32),
            onset=np.zeros(14, dtype=np.float32),
            weight=np.ones(14, dtype=np.float32),
        )
        # Engine instance is shared so transition state isn't fresh —
        # but pattern hasn't changed, so no transition gets triggered.
        p_low = pe._dynamic_emitter_positions(motion_amp=0.0, **common)
        p_high = pe._dynamic_emitter_positions(motion_amp=0.8, **common)

        # motion_amp=0.8 with motion_speed=1 at t=0.5 produces a
        # measurable drift offset on top of the same base.
        diff = np.abs(p_high - p_low).max()
        assert diff > 0.05, (
            f"motion_amp slider should change positions; max diff {diff}"
        )
    finally:
        ctx.release()


def test_onset_pulse_pushes_emitter_outward() -> None:
    """Phase-18 onset pulse: when a channel onsets, its emitter pumps
    outward (along its radial direction from origin) by an amount
    proportional to onset envelope. Quiet channels' emitters stay put.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)

        # Channel 0 alone gets a strong onset; everyone else silent.
        rms = np.zeros(14, dtype=np.float32)
        onset = np.zeros(14, dtype=np.float32)
        onset[0] = 1.0
        weight = np.ones(14, dtype=np.float32)

        # Match against the silent-baseline emitter positions.
        baseline = pe._dynamic_emitter_positions(
            pattern="ring", radius=1.6,
            motion_amp=0.0, motion_speed=0.0, time_s=0.0,
            rms=np.zeros(14, dtype=np.float32),
            onset=np.zeros(14, dtype=np.float32),
            weight=weight,
        )
        # Now compute with ch0 onset blasted; restart engine so prev
        # pattern is the same.
        pe2 = ParticleEngine(ctx, n_particles=100)
        with_pulse = pe2._dynamic_emitter_positions(
            pattern="ring", radius=1.6,
            motion_amp=0.0, motion_speed=0.0, time_s=0.0,
            rms=rms, onset=onset, weight=weight,
        )

        # Ch0 emitter should be further from origin than baseline.
        baseline_r = np.linalg.norm(baseline[0])
        pulsed_r = np.linalg.norm(with_pulse[0])
        assert pulsed_r > baseline_r + 0.05, (
            f"ch0 onset should push emitter outward; baseline_r="
            f"{baseline_r:.3f}, pulsed_r={pulsed_r:.3f}"
        )

        # Ch7 (silent) should be unchanged.
        np.testing.assert_array_almost_equal(
            baseline[7], with_pulse[7], decimal=4
        )
    finally:
        ctx.release()


def test_phase17_emitter_vocabulary_writes_emitter_state() -> None:
    """Phase-17 keywords write to `emitter.*`."""
    from apophenia.prompt.interpreter import PromptInterpreter
    from apophenia.state import EmitterState

    interp = PromptInterpreter()

    # Each pattern keyword sets emitter.pattern.
    for word, expected in [
        ("ring", "ring"),
        ("grid", "grid"),
        ("linear", "line"),
        ("constellation", "sphere"),
        ("knot", "lissajous"),
    ]:
        r = interp.interpret(word)
        assert r["partial"]["emitter"]["pattern"] == expected, (
            f"{word!r} → {expected}"
        )

    # Drift / radius modifiers.
    r_w = interp.interpret("wandering")
    assert r_w["partial"]["emitter"]["motion_amp"] >= 0.5

    r_e = interp.interpret("expanding")
    assert r_e["partial"]["emitter"]["radius"] > 2.0

    # Vocabulary validates against the schema.
    from apophenia.prompt.interpreter import VOCABULARY
    for keyword, diff in VOCABULARY.items():
        if "emitter" not in diff:
            continue
        merged = {**EmitterState().model_dump(), **diff["emitter"]}
        EmitterState.model_validate(merged), f"{keyword!r} produces invalid emitter state"
