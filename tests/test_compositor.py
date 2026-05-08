"""Tests for the GL post-FX compositor.

Phase-14 split: the old `test_shader_engine.py` covered both the
14-layer fragment-shader engine (now deleted) and the post-FX
compositor. The compositor stayed; this file is the residual test
surface — passthrough, saturation, kaleidoscope, glitch, chromatic,
and the phase-11 trail accumulation.

GL-context tests auto-skip when no display is available.
"""

from __future__ import annotations

import numpy as np
import pytest


def _try_make_ctx():
    try:
        import moderngl
        return moderngl.create_standalone_context()
    except Exception:
        return None


def _paint_shader_fbo(comp, size, rgba_bytes):
    """Helper: write `rgba_bytes` directly into the compositor's
    offscreen FBO texture so we can drive the post-FX pipeline with
    an arbitrary 2-D pattern without needing a real renderer.
    """
    comp.offscreen_fbo(size)
    comp._shader_tex.write(rgba_bytes)


def _read_pixel(fbo, size, x, y):
    raw = fbo.read(components=4, dtype="f1")
    idx = (y * size[0] + x) * 4
    return raw[idx], raw[idx + 1], raw[idx + 2]


# --------------------------------------------------------------------------- #
# Pipeline basics
# --------------------------------------------------------------------------- #


def test_compositor_passthrough_preserves_colour() -> None:
    """All-defaults compositor render: a solid pattern survives unchanged."""
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 0] = 255  # red
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render()

        idx = (8 * size[0] + 8) * 4
        raw = out_fbo.read(components=4, dtype="f1")
        assert raw[idx] >= 240, f"R should pass through; got {raw[idx]}"
        assert raw[idx + 2] <= 15
    finally:
        ctx.release()


def test_compositor_saturation_zero_collapses_to_grey() -> None:
    """saturation=0 should drop chroma — a red input emerges as grey."""
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 0] = 255
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=0.0)

        raw = out_fbo.read(components=4, dtype="f1")
        idx = (8 * size[0] + 8) * 4
        # luma = 0.299 R = 76 for R=255. With sat=0 that flows to all channels.
        assert 60 <= raw[idx] <= 90
        assert 60 <= raw[idx + 1] <= 90
        assert 60 <= raw[idx + 2] <= 90
    finally:
        ctx.release()


# --------------------------------------------------------------------------- #
# Kaleidoscope
# --------------------------------------------------------------------------- #


def test_kaleidoscope_2_left_right_symmetric() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (48, 48)
        rgba = np.zeros((48, 48, 4), dtype=np.uint8)
        rgba[:, :24, 2] = 255  # left = blue
        rgba[:, 24:, 1] = 255  # right = green
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(kaleidoscope_segments=2)

        raw = out_fbo.read(components=4, dtype="f1")
        matches = 0
        total = 0
        for y in range(0, size[1], 4):
            for x in range(0, size[0] // 2, 4):
                lx = x
                rx = size[0] - 1 - x
                li = (y * size[0] + lx) * 4
                ri = (y * size[0] + rx) * 4
                if all(abs(raw[li + c] - raw[ri + c]) < 40 for c in range(3)):
                    matches += 1
                total += 1
        assert matches / total > 0.7
    finally:
        ctx.release()


def test_kaleidoscope_1_is_identity() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (32, 32)
        rgba = np.zeros((32, 32, 4), dtype=np.uint8)
        rgba[:, :16, 2] = 255  # blue left
        rgba[:, 16:, 1] = 255  # green right
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(kaleidoscope_segments=1)

        r1, g1, b1 = _read_pixel(out_fbo, size, 4, 16)
        r2, g2, b2 = _read_pixel(out_fbo, size, 28, 16)
        assert b1 > 200 and g1 < 60
        assert g2 > 200 and b2 < 60
    finally:
        ctx.release()


# --------------------------------------------------------------------------- #
# Chromatic + glitch
# --------------------------------------------------------------------------- #


def test_chromatic_separates_rgb_at_edges() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (96, 16)
        rgba = np.zeros((16, 96, 4), dtype=np.uint8)
        rgba[:, :48, :3] = 255
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(chromatic=1.0)
        raw_chrom = out_fbo.read(components=4, dtype="f1")

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(chromatic=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        y = size[1] // 2
        x_just_dark = 49
        idx = (y * size[0] + x_just_dark) * 4
        assert raw_chrom[idx] > raw_no[idx] + 30
        x_just_bright = 46
        idx2 = (y * size[0] + x_just_bright) * 4
        assert raw_chrom[idx2 + 2] < raw_no[idx2 + 2] - 30
    finally:
        ctx.release()


def test_glitch_displaces_some_rows() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (64, 64)
        rgba = np.zeros((64, 64, 4), dtype=np.uint8)
        rgba[:, :32, 0] = 255
        rgba[:, 32:, 1] = 255
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(glitch=1.0, time_s=0.0)
        raw_glitch = out_fbo.read(components=4, dtype="f1")

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(glitch=0.0, time_s=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        diff = sum(
            1 for i in range(0, len(raw_glitch), 4)
            if abs(raw_glitch[i] - raw_no[i]) > 50
            or abs(raw_glitch[i + 1] - raw_no[i + 1]) > 50
        )
        assert diff > 20, f"glitch should displace many pixels; got diff count {diff}"
    finally:
        ctx.release()


# --------------------------------------------------------------------------- #
# Trail (phase 11)
# --------------------------------------------------------------------------- #


def test_trail_zero_is_identity() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 1] = 200
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(trail=0.0)

        idx = (8 * size[0] + 8) * 4
        raw = out_fbo.read(components=4, dtype="f1")
        assert 180 <= raw[idx + 1] <= 215
    finally:
        ctx.release()


def test_trail_retains_decayed_previous_frame() -> None:
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)

        # Frame 1: red.
        red = np.zeros((16, 16, 4), dtype=np.uint8)
        red[..., 0] = 255
        red[..., 3] = 255
        _paint_shader_fbo(comp, size, red.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(trail=0.7)

        idx = (8 * size[0] + 8) * 4
        raw1 = out_fbo.read(components=4, dtype="f1")
        assert raw1[idx] >= 240

        # Frame 2: black input.
        black = np.zeros((16, 16, 4), dtype=np.uint8)
        black[..., 3] = 255
        _paint_shader_fbo(comp, size, black.tobytes())

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(trail=0.7)

        raw2 = out_fbo.read(components=4, dtype="f1")
        assert 150 <= raw2[idx] <= 210
        assert raw2[idx + 1] < 30
        assert raw2[idx + 2] < 30
    finally:
        ctx.release()
