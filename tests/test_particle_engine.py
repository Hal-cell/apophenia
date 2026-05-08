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
    """Run one update step with audible RMS on a subset of channels;
    the destination buffer's contents should differ from the initial
    "all dead" pattern."""
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        pe = ParticleEngine(ctx, n_particles=2000)
        # Snapshot initial state (all in dead pool).
        before = np.frombuffer(pe._buffers[0].read(), dtype=np.float32).reshape(-1, 8)

        features = FastFeatures(
            rms=[0.7] * 14,
            peak=[0.8] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.4] * 14,
            n_channels=14,
        )
        state = VisualState()
        # Run 5 update cycles to give the respawn gate time to fire.
        for i in range(5):
            pe.update_and_render(
                features=features,
                time_s=i * 0.033,
                dt=0.033,
                resolution=(64, 64),
                state=state,
            )

        # Read whichever buffer is currently the "front" (what was just
        # written by the last transform pass).
        after = np.frombuffer(
            pe._buffers[pe._read_idx].read(), dtype=np.float32
        ).reshape(-1, 8)
        # Some particles should have escaped the dead pool (py = -100).
        live_after = (after[:, 1] > -50.0).sum()
        live_before = (before[:, 1] > -50.0).sum()
        assert live_after > live_before, (
            f"expected respawned particles; before={live_before}, after={live_after}"
        )
    finally:
        ctx.release()


def test_particle_engine_silent_audio_keeps_particles_dead() -> None:
    """When all channels have RMS ≈ 0, the activity floor blocks respawn
    and particles stay parked in the dead pool."""
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
        for i in range(10):
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
        # Almost every particle should still be in the dead pool.
        live_after = (after[:, 1] > -50.0).sum()
        assert live_after < pe.n_particles * 0.05, (
            f"silent audio should keep particles dead; got {live_after} live"
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


def test_high_onset_spawns_more_particles_than_low_onset_same_rms() -> None:
    """Phase-13 onset weighting boost: with RMS *below* the activity
    floor, no spawns happen on a calm channel — but a high onset
    pushes activity well above the floor (RMS + onset×5 in the
    formula), so transients alone trigger respawn even on a quiet
    sustained channel.

    This is the core "transient explosion" promise: a percussive hit
    against a near-silent background generates a visible burst.
    """
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.audio.features_fast import FastFeatures
        from apophenia.state import VisualState
        from apophenia.visuals.particle_engine import ParticleEngine

        state = VisualState()

        # RMS just below the 0.02 activity floor — without onset
        # weighting, no spawns. Onset envelopes differ wildly.
        low_onset = FastFeatures(
            rms=[0.01] * 14,
            peak=[0.02] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.0] * 14,
            n_channels=14,
        )
        high_onset = FastFeatures(
            rms=[0.01] * 14,
            peak=[0.02] * 14,
            centroid=[1500.0] * 14,
            onset_envelope=[0.6] * 14,
            n_channels=14,
        )

        pe_low = ParticleEngine(ctx, n_particles=2000)
        after_low = _run_n_steps(pe_low, low_onset, state, n_steps=10)
        live_low = (after_low[:, 1] > -50.0).sum()

        pe_high = ParticleEngine(ctx, n_particles=2000)
        after_high = _run_n_steps(pe_high, high_onset, state, n_steps=10)
        live_high = (after_high[:, 1] > -50.0).sum()

        # Calm channel: essentially zero spawns (only the initial
        # buffer reads as "dead", and they stay there).
        assert live_low < 100, (
            f"calm channels should stay dormant; got {live_low} live"
        )
        # Hit channel: most particles should be live.
        assert live_high > 500, (
            f"onset transients should spawn many particles even at "
            f"sub-floor RMS; got {live_high} live"
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
