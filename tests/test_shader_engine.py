"""Tests for the shader engine.

Most of phase 3 is GLSL — visual correctness is validated by eye, not
by automation. These tests cover the Python-side scaffolding:
  * Layer config validation (preset name, channel range)
  * Centroid → hue mapping math
  * Shader file inventory (every preset has a .frag on disk)
  * Standalone-context render, if available, with a synthetic
    FastFeatures payload — proves shaders compile + a draw call works.

The render test is skipped when no GL context can be created (CI hosts,
sandboxed envs). On M3 Max it runs and is fast.
"""

from __future__ import annotations

import pytest

from apophenia.visuals.shader_engine import (
    CENTROID_HI,
    CENTROID_LO,
    DEFAULT_LAYERS,
    HUE_HI,
    HUE_LO,
    PRESETS,
    SHADER_DIR,
    Layer,
    ShaderEngine,
    centroid_to_hue,
)

# --------------------------------------------------------------------------- #
# centroid_to_hue
# --------------------------------------------------------------------------- #


def test_hue_clamps_at_low() -> None:
    assert centroid_to_hue(0.0) == HUE_LO
    assert centroid_to_hue(CENTROID_LO) == HUE_LO


def test_hue_clamps_at_high() -> None:
    assert centroid_to_hue(50_000.0) == HUE_HI
    assert centroid_to_hue(CENTROID_HI) == HUE_HI


def test_hue_interpolates_linearly() -> None:
    mid = (CENTROID_LO + CENTROID_HI) / 2
    expected_mid = (HUE_LO + HUE_HI) / 2
    assert centroid_to_hue(mid) == pytest.approx(expected_mid, abs=0.5)


# --------------------------------------------------------------------------- #
# Shader file inventory
# --------------------------------------------------------------------------- #


def test_shared_vertex_shader_exists() -> None:
    assert (SHADER_DIR / "quad.vert").is_file()


@pytest.mark.parametrize("preset", PRESETS)
def test_each_preset_has_a_fragment_shader(preset: str) -> None:
    path = SHADER_DIR / f"{preset}.frag"
    assert path.is_file(), f"missing fragment shader: {path}"
    body = path.read_text()
    assert body.startswith("#version 330"), (
        f"{preset}.frag should declare #version 330 on the first line"
    )
    assert "fragColor" in body, f"{preset}.frag should write `fragColor`"


def test_default_layers_use_only_known_presets() -> None:
    for layer in DEFAULT_LAYERS:
        assert layer.preset in PRESETS, f"unknown preset in default layers: {layer.preset!r}"
        assert 0 <= layer.channel < 14, f"channel out of range: {layer.channel}"


def test_default_layer_count_matches_channels() -> None:
    """Ship one layer per channel by default. Users can rebind later, but
    the default is 1:1 so first-run users see all 14 inputs reflected."""
    assert len(DEFAULT_LAYERS) == 14
    channels_used = sorted(layer.channel for layer in DEFAULT_LAYERS)
    assert channels_used == list(range(14))


# --------------------------------------------------------------------------- #
# Layer / engine validation
# --------------------------------------------------------------------------- #


def _try_make_ctx():
    """Try to spin up a standalone GL context; return None if unavailable
    (CI hosts without a display)."""
    try:
        import moderngl
        return moderngl.create_standalone_context()
    except Exception:
        return None


def test_engine_rejects_unknown_preset() -> None:
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        with pytest.raises(ValueError, match="unknown preset"):
            ShaderEngine(ctx, layers=[Layer(preset="nope", channel=0)])
    finally:
        ctx.release()


def test_engine_rejects_negative_channel() -> None:
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        with pytest.raises(ValueError, match="channel"):
            # Use a *valid* preset name so we exercise the channel-bounds
            # check, not the unknown-preset check.
            ShaderEngine(ctx, layers=[Layer(preset="flow", channel=-1)])
    finally:
        ctx.release()


def test_engine_compiles_all_default_shaders() -> None:
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        engine = ShaderEngine(ctx)
        # Every distinct preset in DEFAULT_LAYERS should have a built program.
        used = {layer.preset for layer in DEFAULT_LAYERS}
        assert set(engine.programs.keys()) == used
        # And one VAO per program.
        assert set(engine.vaos.keys()) == used
    finally:
        ctx.release()


def test_engine_render_produces_nonblack_output() -> None:
    """Render to an offscreen framebuffer; verify at least one pixel is lit.

    Catches regressions where uniforms get wired wrong and everything
    multiplies to zero, or where the additive blend gets configured
    such that nothing shows up.
    """

    from apophenia.audio.features_fast import FastFeatures

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        engine = ShaderEngine(ctx)
        size = (256, 256)
        tex = ctx.texture(size, components=4, dtype="f1")
        fbo = ctx.framebuffer(color_attachments=[tex])
        fbo.use()
        ctx.viewport = (0, 0, *size)

        # Loud hits across all channels with various centroids so every
        # preset gets non-trivial input.
        features = FastFeatures(
            rms=[0.5] * 14,
            peak=[0.5] * 14,
            centroid=[100.0 + i * 800.0 for i in range(14)],
            onset_envelope=[0.8] * 14,
            n_channels=14,
        )
        engine.render(features, time_s=1.0, resolution=size)

        # Read back the framebuffer; assert non-black.
        raw = fbo.read(components=4, dtype="f1")
        # raw is bytes — count non-zero bytes.
        assert any(b > 0 for b in raw), "render produced an all-black framebuffer"
    finally:
        ctx.release()


def _paint_shader_fbo(comp, size, rgba_bytes):
    """Helper: write `rgba_bytes` directly into the compositor's
    offscreen FBO texture. Lets us drive the post-FX pipeline with an
    arbitrary 2-D pattern without needing a full ShaderEngine pass.
    Bytes layout: tightly packed RGBA uint8, row-major, length =
    size[0] * size[1] * 4.
    """
    comp.offscreen_fbo(size)  # ensures _shader_tex is allocated at this size
    comp._shader_tex.write(rgba_bytes)


def test_compositor_passthrough_preserves_shader_colour() -> None:
    """All-defaults compositor render: a solid shader pattern survives
    unchanged through the post-FX chain."""
    import numpy as np

    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)

        # Paint solid red into the shader FBO via direct texture write.
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 0] = 255  # R
        rgba[..., 3] = 255  # A
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render()  # all defaults: should be identity

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        assert raw[idx] >= 240, f"R should be ~255 at centre, got {raw[idx]}"
        assert raw[idx + 2] <= 15, f"B should be ~0 at centre, got {raw[idx + 2]}"
    finally:
        ctx.release()


def test_compositor_saturation_zero_collapses_to_grey() -> None:
    """saturation=0 should drop chroma — a red input emerges as grey."""
    import numpy as np

    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        rgba = np.zeros((16, 16, 4), dtype=np.uint8)
        rgba[..., 0] = 255  # solid red
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=0.0)

        raw = out_fbo.read(components=4, dtype="f1")
        idx = (8 * size[0] + 8) * 4
        # luma = 0.299 R = 76 for R=255. With sat=0 that goes to all channels.
        # Allow a wide tolerance for the LINEAR sampler / float-precision drift.
        assert 60 <= raw[idx] <= 90
        assert 60 <= raw[idx + 1] <= 90
        assert 60 <= raw[idx + 2] <= 90
    finally:
        ctx.release()


@pytest.mark.parametrize("preset", PRESETS)
def test_each_shader_renders_nonblack_when_driven(preset: str) -> None:
    """Each phase-9 preset, fed audible RMS + a centroid + an onset
    envelope, must produce visible output. Catches uniform-name
    regressions and silent zero-multiplications.
    """
    import moderngl  # noqa: F401

    from apophenia.audio.features_fast import FastFeatures

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        engine = ShaderEngine(ctx, layers=[Layer(preset=preset, channel=0)])
        size = (128, 128)
        tex = ctx.texture(size, components=4, dtype="f1")
        fbo = ctx.framebuffer(color_attachments=[tex])
        fbo.use()
        ctx.viewport = (0, 0, *size)

        features = FastFeatures(
            rms=[0.6] + [0.0] * 13,
            peak=[0.7] + [0.0] * 13,
            centroid=[2000.0] + [0.0] * 13,
            onset_envelope=[0.9] + [0.0] * 13,
            n_channels=14,
        )
        engine.render(features, time_s=2.0, resolution=size)

        raw = fbo.read(components=4, dtype="f1")
        # Count pixels that have any non-trivial colour. Some of the
        # presets are heavily falloff-masked so most of the screen will
        # be near-black; we only need a meaningful patch to be lit.
        bright_pixels = sum(
            1 for i in range(0, len(raw), 4)
            if raw[i] > 20 or raw[i + 1] > 20 or raw[i + 2] > 20
        )
        total = len(raw) // 4
        assert bright_pixels > 50, (
            f"{preset}: only {bright_pixels}/{total} bright pixels — "
            f"shader may have a uniform / falloff bug"
        )
    finally:
        ctx.release()


def _composite_setup(ctx, size=(64, 64), shader_rgb=(1.0, 0.0, 0.0)):
    """Helper: build a Compositor, render `shader_rgb` into the offscreen
    FBO, and return (compositor, output_fbo). Caller does the actual
    composite render call to `output_fbo` and reads it back.
    """
    from apophenia.visuals.shader_engine import Compositor

    comp = Compositor(ctx)
    fbo = comp.offscreen_fbo(size)
    fbo.use()
    ctx.clear(*shader_rgb, 1.0)
    ctx.viewport = (0, 0, *size)

    out_tex = ctx.texture(size, components=4, dtype="f1")
    out_fbo = ctx.framebuffer(color_attachments=[out_tex])
    return comp, out_fbo, size


def _read_pixel(fbo, size, x, y):
    """Sample one pixel from `fbo` at (x, y) and return (r, g, b)."""
    raw = fbo.read(components=4, dtype="f1")
    idx = (y * size[0] + x) * 4
    return raw[idx], raw[idx + 1], raw[idx + 2]


def test_compositor_kaleidoscope_2_segments_left_right_symmetric() -> None:
    """kaleidoscope=2 (180° wedge mirrored) should leave the output
    symmetric across the vertical mid-line."""
    import numpy as np

    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (48, 48)

        # Asymmetric shader-FBO content: left half blue, right half green.
        rgba = np.zeros((48, 48, 4), dtype=np.uint8)
        rgba[:, :24, 2] = 255
        rgba[:, 24:, 1] = 255
        rgba[..., 3] = 255
        _paint_shader_fbo(comp, size, rgba.tobytes())

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(kaleidoscope_segments=2)

        raw = out_fbo.read(components=4, dtype="f1")
        # Compare left half to mirrored right half — at least 70% of
        # corresponding pixels should match within tolerance (LINEAR
        # interp + atan rounding leave a thin diagonal seam).
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
        assert matches / total > 0.7, (
            f"kaleidoscope=2 should be ~mirror-symmetric, only {matches}/{total} match"
        )
    finally:
        ctx.release()


def test_compositor_chromatic_separates_rgb_at_edges() -> None:
    """A vertical bright/dark edge with chromatic aberration produces
    R/B fringes — R leaks into the dark side, B leaks out of the bright."""
    import numpy as np

    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (96, 16)

        # White left half, black right half — sharp edge at x=48.
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
        # x=49: just inside the dark side. Red sample at x-aberr lands
        # in the bright region → R bleeds in.
        x_just_dark = 49
        idx = (y * size[0] + x_just_dark) * 4
        assert raw_chrom[idx] > raw_no[idx] + 30, (
            f"red should leak into dark side; got R={raw_chrom[idx]} "
            f"(chrom) vs R={raw_no[idx]} (no chrom)"
        )
        # x=46: just inside the bright side. Blue sample at x+aberr lands
        # in the dark region → B drops below 255.
        x_just_bright = 46
        idx2 = (y * size[0] + x_just_bright) * 4
        assert raw_chrom[idx2 + 2] < raw_no[idx2 + 2] - 30, (
            f"blue should leak out of bright side; got B={raw_chrom[idx2 + 2]} "
            f"(chrom) vs B={raw_no[idx2 + 2]} (no chrom)"
        )
    finally:
        ctx.release()


def test_compositor_glitch_displaces_some_rows() -> None:
    """Glitch=1 produces row-level horizontal displacement so the output
    differs from glitch=0."""
    import numpy as np

    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (64, 64)

        # Vertical red/green split.
        rgba = np.zeros((64, 64, 4), dtype=np.uint8)
        rgba[:, :32, 0] = 255  # red left
        rgba[:, 32:, 1] = 255  # green right
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


def test_compositor_kaleidoscope_1_is_identity() -> None:
    """kaleidoscope=1 must leave UV untouched — output equals input."""
    import numpy as np

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


def test_engine_render_with_zero_channel_weights_is_black() -> None:
    """When all channel weights are 0, every layer's u_channel_weight is
    zero, so shaders multiply to nothing → frame is solid black.
    """
    from apophenia.audio.features_fast import FastFeatures
    from apophenia.state import VisualState

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        engine = ShaderEngine(ctx)
        size = (64, 64)
        tex = ctx.texture(size, components=4, dtype="f1")
        fbo = ctx.framebuffer(color_attachments=[tex])
        fbo.use()
        ctx.viewport = (0, 0, *size)

        features = FastFeatures(
            rms=[0.5] * 14,
            peak=[0.5] * 14,
            centroid=[1000.0] * 14,
            onset_envelope=[0.8] * 14,
            n_channels=14,
        )
        # Build a state with all channels muted.
        state = VisualState(channel_weight=[0.0] * 14)
        engine.render(features, time_s=1.0, resolution=size, state=state)

        raw = fbo.read(components=4, dtype="f1")
        # The clear sets RGB=0, A=255 (full alpha). With every layer
        # multiplying by zero, RGB should remain zero.
        # Read back as RGBA bytes; check RGB channels.
        for i in range(0, len(raw), 4):
            assert raw[i] == 0, f"R != 0 at pixel {i // 4}"
            assert raw[i + 1] == 0, f"G != 0 at pixel {i // 4}"
            assert raw[i + 2] == 0, f"B != 0 at pixel {i // 4}"
    finally:
        ctx.release()
