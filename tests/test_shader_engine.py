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
            ShaderEngine(ctx, layers=[Layer(preset="vignette", channel=-1)])
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


def test_compositor_blend_zero_returns_shader_color() -> None:
    """blend=0 + has_ai=1: the composite output must equal the shader FBO
    contents (the AI texture should be ignored)."""
    import numpy as np

    from apophenia.ai.bus import AIFrame
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (32, 32)
        fbo = comp.offscreen_fbo(size)

        # Paint the offscreen FBO solid red.
        fbo.use()
        ctx.clear(1.0, 0.0, 0.0, 1.0)
        ctx.viewport = (0, 0, *size)

        # Upload a solid-blue AI frame.
        blue = np.zeros((16, 16, 3), dtype=np.uint8)
        blue[..., 2] = 255
        comp.maybe_upload_ai_frame(AIFrame(image=blue, gen_count=1))

        # Render composite to a separate output FBO.
        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=0.0, saturation=1.0, has_ai=True)

        raw = out_fbo.read(components=4, dtype="f1")
        # Sample the centre pixel: red dominates, blue near zero.
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        assert raw[idx] >= 240, f"R should be ~255 at centre, got {raw[idx]}"
        assert raw[idx + 2] <= 15, f"B should be ~0 at centre, got {raw[idx + 2]}"
    finally:
        ctx.release()


def test_compositor_blend_one_returns_ai_color() -> None:
    """blend=1 + has_ai=1: the composite output must equal the AI texture."""
    import numpy as np

    from apophenia.ai.bus import AIFrame
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (32, 32)
        fbo = comp.offscreen_fbo(size)

        fbo.use()
        ctx.clear(1.0, 0.0, 0.0, 1.0)  # red shader
        ctx.viewport = (0, 0, *size)

        blue = np.zeros((16, 16, 3), dtype=np.uint8)
        blue[..., 2] = 255
        comp.maybe_upload_ai_frame(AIFrame(image=blue, gen_count=1))

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        assert raw[idx] <= 15, f"R should be ~0 at centre, got {raw[idx]}"
        assert raw[idx + 2] >= 240, f"B should be ~255 at centre, got {raw[idx + 2]}"
    finally:
        ctx.release()


def test_compositor_has_ai_zero_falls_back_to_shader() -> None:
    """has_ai=0 (no AI frame yet) → composite ignores blend, shader wins."""
    import numpy as np

    from apophenia.ai.bus import AIFrame
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        fbo = comp.offscreen_fbo(size)

        fbo.use()
        ctx.clear(1.0, 0.0, 0.0, 1.0)  # red shader
        ctx.viewport = (0, 0, *size)

        # Upload a blue AI frame so the texture is non-default — but we
        # tell render() that AI isn't really active yet.
        blue = np.full((16, 16, 3), [0, 0, 255], dtype=np.uint8)
        comp.maybe_upload_ai_frame(AIFrame(image=blue, gen_count=1))

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        # blend=1 would ordinarily show 100% AI, but has_ai=False forces 0.
        comp.render(blend=1.0, saturation=1.0, has_ai=False)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        # Shader red should win.
        assert raw[idx] >= 240, f"R should be ~255 at centre, got {raw[idx]}"
    finally:
        ctx.release()


def test_compositor_skips_redundant_ai_uploads() -> None:
    """Same gen_count → no upload. New gen_count → upload."""
    import numpy as np

    from apophenia.ai.bus import AIFrame
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        f1 = AIFrame(image=np.zeros((4, 4, 3), dtype=np.uint8), gen_count=1)
        f1_again = AIFrame(image=np.zeros((4, 4, 3), dtype=np.uint8), gen_count=1)
        f2 = AIFrame(image=np.zeros((4, 4, 3), dtype=np.uint8), gen_count=2)
        assert comp.maybe_upload_ai_frame(f1) is True
        assert comp.maybe_upload_ai_frame(f1_again) is False
        assert comp.maybe_upload_ai_frame(f2) is True
        assert comp.maybe_upload_ai_frame(None) is False
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
