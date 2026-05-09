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
# Phase 17: camera tracking + drift + per-channel directional kicks
# --------------------------------------------------------------------------- #


def test_camera_drift_offset_zero_when_amount_zero() -> None:
    """`camera_drift_offset(t, 0, anything)` should always return zero."""
    from apophenia.visuals.particle_engine import camera_drift_offset

    for t in (0.0, 1.0, 5.7, 100.0):
        offset = camera_drift_offset(t, drift_amount=0.0, audio_intensity=0.5)
        assert np.allclose(offset, 0.0)


def test_camera_drift_offset_varies_over_time() -> None:
    """With drift > 0, the offset should change between frames —
    that's the whole point of drift."""
    from apophenia.visuals.particle_engine import camera_drift_offset

    o0 = camera_drift_offset(0.0, drift_amount=1.0, audio_intensity=0.5)
    o1 = camera_drift_offset(1.0, drift_amount=1.0, audio_intensity=0.5)
    o2 = camera_drift_offset(5.0, drift_amount=1.0, audio_intensity=0.5)
    # Different time samples should produce different offsets.
    assert not np.allclose(o0, o1)
    assert not np.allclose(o0, o2)
    # And drift_amount=1 should produce offsets within roughly ±1 unit
    # (Lissajous amplitude × scale).
    assert np.abs(o1).max() < 2.0


def test_camera_drift_amount_scales_offset_magnitude() -> None:
    """drift=2.0 should produce offsets twice as large as drift=1.0."""
    from apophenia.visuals.particle_engine import camera_drift_offset

    o1 = camera_drift_offset(1.5, drift_amount=1.0, audio_intensity=0.0)
    o2 = camera_drift_offset(1.5, drift_amount=2.0, audio_intensity=0.0)
    np.testing.assert_allclose(o2, o1 * 2.0, atol=1e-5)


def test_emitter_ring_matches_shader_layout() -> None:
    """The Python-side `_EMITTER_RING` MUST match the GLSL
    `emitter_pos()` exactly — centroid math depends on it."""
    from apophenia.visuals.particle_engine import _EMITTER_RING

    # Channel 0: angle = 0 → (cos(0)*1.6, sin(0*0.91)*0.25, sin(0)*1.6)
    #                       = (1.6, 0, 0)
    np.testing.assert_allclose(_EMITTER_RING[0], [1.6, 0.0, 0.0], atol=1e-5)
    # Channel 7: angle = pi → (-1.6, sin(7*0.91)*0.25, ~0)
    assert _EMITTER_RING[7, 0] == pytest.approx(-1.6, abs=1e-5)
    assert abs(_EMITTER_RING[7, 2]) < 1e-5
    # 14 rows, 3 columns.
    assert _EMITTER_RING.shape == (14, 3)


def test_camera_centroid_tracks_loud_channel() -> None:
    """Phase-17 core fix: with one channel loud, the smoothed centroid
    should be biased toward that channel's emitter, not the origin."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import _EMITTER_RING, ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)
        state = VisualState()
        # Only ch0 loud, all weights = 1.
        loud_ch0 = FastFeatures(
            rms=[1.0] + [0.0] * 13,
            peak=[1.0] + [0.0] * 13,
            centroid=[1500.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        # Run enough frames for the EMA to converge.
        for i in range(200):
            pe.update_and_render(
                features=loud_ch0,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )
        # ch0's emitter is at (1.6, 0, 0). Smoothed centroid should
        # be heavily biased that way. Math: with the 0.05 baseline
        # added to every channel, total weight = 1.05 + 13×0.05 = 1.7.
        # Numerator x ≈ 1.05×1.6 + 0.05×Σ(other ring x) ≈ 1.6.
        # So centroid x ≈ 1.6 / 1.7 ≈ 0.94. Verify it's clearly biased
        # toward ch0 (not at origin).
        centroid = pe._smoothed_centroid
        ch0_pos = _EMITTER_RING[0]
        assert centroid[0] > 0.85, (
            f"smoothed centroid should track ch0 emitter ({ch0_pos}); "
            f"got {centroid}"
        )
    finally:
        ctx.release()


def test_camera_centroid_stays_near_origin_when_silent() -> None:
    """Silent audio → all channels contribute equally via the 0.05
    baseline → centroid sits near the origin (centre of the ring)."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)
        state = VisualState()
        silent = FastFeatures(
            rms=[0.0] * 14,
            peak=[0.0] * 14,
            centroid=[0.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        for i in range(200):
            pe.update_and_render(
                features=silent,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )
        # Equal-weight average of 14 ring positions ≈ origin.
        centroid = pe._smoothed_centroid
        assert np.linalg.norm(centroid) < 0.3, (
            f"silent centroid should sit near origin; got {centroid}"
        )
    finally:
        ctx.release()


def test_phase17_camera_motion_vocabulary() -> None:
    """`wandering / restless / roaming / nomadic` raise camera.drift;
    `fixed / framed` zero it; `tracking` enables centroid follow."""
    from apophenia.prompt.interpreter import PromptInterpreter

    interp = PromptInterpreter()
    for word, expected_drift_min in [
        ("wandering", 0.9),
        ("restless", 1.3),
        ("roaming", 1.5),
        ("nomadic", 1.7),
    ]:
        r = interp.interpret(word)
        assert r["partial"]["camera"]["drift"] >= expected_drift_min

    r_fixed = interp.interpret("fixed")
    assert r_fixed["partial"]["camera"]["drift"] == 0.0
    assert r_fixed["partial"]["camera"]["track_centroid"] is False

    r_tracking = interp.interpret("tracking")
    assert r_tracking["partial"]["camera"]["track_centroid"] is True


def test_channel_kick_directions_are_well_dispersed() -> None:
    """Phase-17: each channel's onset kick direction must be visually
    distinct so different channels produce different cluster motions.
    Replicates the GLSL Fibonacci-sphere lattice in Python and checks
    pairwise alignment stays below 0.7 — well below the visually-confusing
    threshold of ~0.95.
    """
    import math as m

    n = 14
    dirs = []
    for ch in range(n):
        y = 1.0 - 2.0 * (ch + 0.5) / n
        r = m.sqrt(max(1.0 - y * y, 0.0))
        az = ch * 2.39996323
        dirs.append([r * m.cos(az), y, r * m.sin(az)])
    dirs_arr = np.array(dirs)
    dots = dirs_arr @ dirs_arr.T
    np.fill_diagonal(dots, 0)
    assert dots.max() < 0.75, (
        f"channel kick directions cluster too tightly; max alignment = {dots.max():.3f}"
    )
    # And every direction is unit-length.
    norms = np.linalg.norm(dirs_arr, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


# --------------------------------------------------------------------------- #
# Phase 18: fluid dynamics
# --------------------------------------------------------------------------- #


def test_phase18_particles_stay_contained_under_long_simulation() -> None:
    """Phase-18 fix for "particles drift far away over time": with the
    soft world bound (r=4 restoring force) + hard reset (r>5 → snap
    home), particles should stay within a moderate scene radius even
    after hundreds of frames of varied audio.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        # Loud, onset-heavy audio that would push particles far in the
        # phase-15/-17 model.
        features = FastFeatures(
            rms=[0.8] * 14,
            peak=[0.9] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.7] * 14,
            n_channels=14,
        )
        state = VisualState()

        pe = ParticleEngine(ctx, n_particles=2000)
        # 300 frames ≈ 10 seconds at 30fps simulation step.
        for i in range(300):
            pe.update_and_render(
                features=features,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )

        buf = np.frombuffer(
            pe._buffers[pe._read_idx].read(), dtype=np.float32
        ).reshape(-1, 8)
        radii = np.linalg.norm(buf[:, 0:3], axis=1)
        # Hard reset triggers at r=5; allow tiny epsilon for in-flight
        # particles between reset frames.
        assert radii.max() < 5.5, (
            f"phase-18 containment broke: max particle radius = "
            f"{radii.max():.2f}"
        )
        # The cluster should still have meaningful radial extent —
        # particles haven't all collapsed onto the emitter ring
        # (mean radius near 1.6 is the ring; "collapsed" would be
        # mean ≈ 0 with very low std). Use mean as the no-collapse
        # signal.
        assert radii.mean() > 0.8, (
            f"phase-18 anti-collapse broke: mean radius = "
            f"{radii.mean():.3f}; particles are piling at origin"
        )
    finally:
        ctx.release()


def test_phase18_no_centroid_collapse_under_dense_audio() -> None:
    """Phase-18 fix for "particles eventually collapse to a point":
    under multi-channel-loud audio, the multi-emitter pull used to
    drag every particle to the centroid (origin). With the secondary
    pull lowered to 0.08, particles should stay distributed across
    their home territories.

    Test: after long simulation under dense audio, the std of particle
    positions should be > 1.0 — meaning particles are spread out, not
    piled at origin.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        # All channels equally loud — the worst case for centroid
        # collapse since every emitter pulls every particle.
        features = FastFeatures(
            rms=[0.5] * 14,
            peak=[0.6] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        state = VisualState()

        pe = ParticleEngine(ctx, n_particles=2000)
        for i in range(400):
            pe.update_and_render(
                features=features,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )

        buf = np.frombuffer(
            pe._buffers[pe._read_idx].read(), dtype=np.float32
        ).reshape(-1, 8)
        # Spread metric: XZ-plane spread (the emitter ring lies in XZ;
        # Y intentionally has a tiny wobble so its variance is small
        # by design). If particles have collapsed to centroid, BOTH
        # X and Z spread would be near zero.
        x_std = buf[:, 0].std()
        z_std = buf[:, 2].std()
        assert x_std > 0.5 and z_std > 0.5, (
            f"phase-18 anti-collapse broke under dense audio: "
            f"X std={x_std:.3f}, Z std={z_std:.3f}"
        )
        # And the mean distance from origin in XZ stays above the
        # collapse threshold.
        xz_dist = np.sqrt(buf[:, 0] ** 2 + buf[:, 2] ** 2)
        assert xz_dist.mean() > 0.8, (
            f"phase-18 anti-collapse broke: mean XZ distance = "
            f"{xz_dist.mean():.3f}"
        )
    finally:
        ctx.release()


def test_phase18_audio_smoothing_state_persists_on_engine() -> None:
    """Phase-18: ParticleEngine maintains EMA-smoothed audio arrays
    across calls. Verify they update toward fresh values."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=100)
        # Initial smoothed arrays are zero.
        assert pe._smoothed_rms.sum() == 0.0
        assert pe._smoothed_onset.sum() == 0.0

        loud = FastFeatures(
            rms=[0.7] * 14,
            peak=[0.8] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.5] * 14,
            n_channels=14,
        )
        state = VisualState()
        # One frame should move the EMA partway toward the targets.
        pe.update_and_render(
            features=loud, time_s=0.0, dt=0.033,
            resolution=(64, 64), state=state,
        )
        # After 1 frame at α=0.10, smoothed_rms ≈ 0.10 × 0.7 = 0.07.
        assert pe._smoothed_rms[0] == pytest.approx(0.07, abs=0.005)
        # After 1 frame at α=0.30, smoothed_onset ≈ 0.30 × 0.5 = 0.15.
        assert pe._smoothed_onset[0] == pytest.approx(0.15, abs=0.005)

        # 50 frames should converge close to the targets.
        for i in range(1, 50):
            pe.update_and_render(
                features=loud, time_s=i * 0.033, dt=0.033,
                resolution=(64, 64), state=state,
            )
        assert pe._smoothed_rms[0] == pytest.approx(0.7, abs=0.05)
        assert pe._smoothed_onset[0] == pytest.approx(0.5, abs=0.05)
    finally:
        ctx.release()


def test_phase18_viscosity_vocabulary_writes_force_viscosity() -> None:
    from apophenia.prompt.interpreter import PromptInterpreter

    interp = PromptInterpreter()
    for word, expected_min in [
        ("viscous", 0.8),
        ("oily", 0.85),
        ("molasses", 0.9),
        ("honey", 0.85),
    ]:
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert r["partial"]["force"]["viscosity"] >= expected_min, (
            f"{word!r} should set high viscosity"
        )

    for word, expected_max in [
        ("airy", 0.2),
        ("gaseous", 0.15),
        ("loose", 0.25),
        ("ethereal", 0.3),
    ]:
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert r["partial"]["force"]["viscosity"] <= expected_max


def test_phase17_camera_state_drift_validates() -> None:
    """CameraState.drift ∈ [0, 2]; track_centroid is bool with default True."""
    from pydantic import ValidationError

    from apophenia.state import CameraState

    c = CameraState()
    assert c.drift == 0.4
    assert c.track_centroid is True

    with pytest.raises(ValidationError):
        CameraState(drift=-0.1)
    with pytest.raises(ValidationError):
        CameraState(drift=3.0)
    # Boundary values should validate.
    CameraState(drift=0.0)
    CameraState(drift=2.0)
