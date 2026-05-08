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

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp, out_fbo, size = _composite_setup(ctx, size=(48, 48), shader_rgb=(0, 0, 0))

        # Asymmetric AI texture: left half blue, right half green.
        ai = np.zeros((48, 48, 3), dtype=np.uint8)
        ai[:, : 48 // 2, 2] = 255
        ai[:, 48 // 2 :, 1] = 255
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1))

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, kaleidoscope_segments=2)

        raw = out_fbo.read(components=4, dtype="f1")
        # Compare left half to mirrored right half — at least 70% of
        # corresponding pixels should match within a small tolerance
        # (LINEAR interp + atan rounding leaves a thin diagonal seam).
        matches = 0
        total = 0
        for y in range(0, size[1], 4):
            for x in range(0, size[0] // 2, 4):
                lx = x
                rx = size[0] - 1 - x
                li = (y * size[0] + lx) * 4
                ri = (y * size[0] + rx) * 4
                # Allow per-channel tolerance of 40 (uint8) since the
                # mirror axis snaps via atan() and LINEAR sampling.
                if all(abs(raw[li + c] - raw[ri + c]) < 40 for c in range(3)):
                    matches += 1
                total += 1
        assert matches / total > 0.7, (
            f"kaleidoscope=2 should be ~mirror-symmetric, only {matches}/{total} match"
        )
    finally:
        ctx.release()


def test_compositor_chromatic_separates_rgb_at_edges() -> None:
    """A vertical AI texture edge (red half / black half) with chromatic
    aberration should produce a thin red and blue fringe near the edge.
    Specifically: there must exist an x where R > B (red leaking out of
    its native region) AND another x where B > R.
    """
    import numpy as np

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (96, 16)
        comp, out_fbo, _ = _composite_setup(ctx, size=size, shader_rgb=(0, 0, 0))

        # AI texture: white left half, black right half — sharp edge in
        # the centre of the screen creates a chromatic split.
        ai = np.zeros((16, 96, 3), dtype=np.uint8)
        ai[:, : 96 // 2] = 255
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1))

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, chromatic=1.0)
        raw_chrom = out_fbo.read(components=4, dtype="f1")

        # Compare against chromatic=0 — the difference should be visible.
        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, chromatic=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        # Mid-row pixel ONE pixel into the dark side (x=49). At
        # chromatic=1, aberr ≈ 0.012 in UV space ≈ 1.15px on a 96-wide
        # texture, so the red sample lands just inside the bright region
        # → R bleeds in, while B does the opposite.
        y = size[1] // 2
        x_just_dark = 96 // 2 + 1
        idx = (y * size[0] + x_just_dark) * 4
        r_chrom = raw_chrom[idx]
        r_no = raw_no[idx]
        assert r_chrom > r_no + 30, (
            f"red should leak into dark side with chromatic on; "
            f"got R={r_chrom} (chrom) vs R={r_no} (no chrom)"
        )

        # Symmetric check: just inside the bright side (x=46), B should be
        # < 255 with chromatic (blue has been pushed out of the bright region).
        x_just_bright = 96 // 2 - 2
        idx2 = (y * size[0] + x_just_bright) * 4
        b_chrom = raw_chrom[idx2 + 2]
        b_no = raw_no[idx2 + 2]
        assert b_chrom < b_no - 30, (
            f"blue should leak out of bright side; "
            f"got B={b_chrom} (chrom) vs B={b_no} (no chrom)"
        )
    finally:
        ctx.release()


def test_compositor_glitch_displaces_some_rows() -> None:
    """Glitch=1 produces row-level horizontal displacement, so the output
    differs from glitch=0 (and is *not* simply a uniform shift)."""
    import numpy as np

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (64, 64)
        comp, out_fbo, _ = _composite_setup(ctx, size=size, shader_rgb=(0, 0, 0))

        # AI texture: vertical red/green split — easy to detect column
        # displacement at any row.
        ai = np.zeros((64, 64, 3), dtype=np.uint8)
        ai[:, : 32, 0] = 255  # red left
        ai[:, 32:, 1] = 255   # green right
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1))

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, glitch=1.0, time_s=0.0)
        raw_glitch = out_fbo.read(components=4, dtype="f1")

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, glitch=0.0, time_s=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        # 40 quantised rows × 15% trigger rate ≈ 6 displaced rows; each
        # displacement is up to ±0.06 UV (≈4px on this 64-wide texture)
        # but only pixels straddling the centre column show a colour
        # change. Empirically that's ~25–60 pixels at this size.
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

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (32, 32)
        comp, out_fbo, _ = _composite_setup(ctx, size=size, shader_rgb=(0, 0, 0))

        ai = np.zeros((32, 32, 3), dtype=np.uint8)
        ai[:, : 16, 2] = 255  # blue left
        ai[:, 16:, 1] = 255   # green right
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1))

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True, kaleidoscope_segments=1)

        # Centre row, x=4 should be ~blue; x=28 should be ~green.
        r1, g1, b1 = _read_pixel(out_fbo, size, 4, 16)
        r2, g2, b2 = _read_pixel(out_fbo, size, 28, 16)
        assert b1 > 200 and g1 < 60
        assert g2 > 200 and b2 < 60
    finally:
        ctx.release()


def test_compositor_first_ai_frame_visible_immediately() -> None:
    """Regression: time-interp must not crossfade the FIRST AI frame from
    the initial black placeholder. With blend=1, has_ai=True, and one
    upload, the output should reflect the AI bytes regardless of how
    much (or little) wallclock has elapsed."""
    import numpy as np

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (32, 32)
        comp, out_fbo, _ = _composite_setup(ctx, size=size, shader_rgb=(0, 0, 0))

        # Solid magenta AI frame.
        ai = np.full((32, 32, 3), [255, 0, 255], dtype=np.uint8)
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1))

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(blend=1.0, saturation=1.0, has_ai=True)
        r, g, b = _read_pixel(out_fbo, size, 16, 16)
        # Should be magenta — not black, not crossfading from the placeholder.
        assert r > 240 and g < 15 and b > 240, f"got R={r} G={g} B={b}"
    finally:
        ctx.release()


def test_compositor_time_interp_period_tracks_observed_cadence() -> None:
    """After two uploads spaced ~T apart, `_ai_period_s` should be near T.
    No GL needed — pure CPU-side test of the EMA."""
    import time

    import numpy as np

    from apophenia.ai.bus import AIFrame

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        from apophenia.visuals.shader_engine import Compositor

        comp = Compositor(ctx)
        ai = np.zeros((4, 4, 3), dtype=np.uint8)

        # First upload — sets timestamp, no period change yet.
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=1, latency_ms=120.0))
        # Wait ~80ms; second upload should push the EMA toward 0.08.
        time.sleep(0.08)
        comp.maybe_upload_ai_frame(AIFrame(image=ai, gen_count=2))

        # EMA started at ~0.12 (from latency_ms), gets pulled toward 0.08
        # with α=0.3 → expected ~ 0.108. Just check it moved in the right
        # direction.
        assert comp._ai_period_s < 0.12
        assert comp._ai_period_s > 0.05
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
