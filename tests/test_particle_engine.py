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
