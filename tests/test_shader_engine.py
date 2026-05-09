"""Tests for the shader engine + compositor.

Most of phase 3 / 9 is GLSL — visual correctness is validated by eye,
not by automation. These tests cover the Python-side scaffolding:
  * Layer config validation (preset name, channel range)
  * Centroid → hue mapping math
  * Shader file inventory (every preset has a .frag on disk)
  * Standalone-context render — proves shaders compile + a draw call
    works. Skipped when no GL context can be created.
  * Compositor pass: kaleidoscope symmetry, chromatic split, glitch
    displacement, identity passthrough at neutral settings, saturation=0
    desat to grey.
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
    """Ship one layer per channel by default."""
    assert len(DEFAULT_LAYERS) == 14
    channels_used = sorted(layer.channel for layer in DEFAULT_LAYERS)
    assert channels_used == list(range(14))


# --------------------------------------------------------------------------- #
# Layer / engine validation
# --------------------------------------------------------------------------- #


def _try_make_ctx():
    """Try to spin up a standalone GL context; return None if unavailable."""
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
            ShaderEngine(ctx, layers=[Layer(preset="flow", channel=-1)])
    finally:
        ctx.release()


def test_engine_compiles_all_default_shaders() -> None:
    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        engine = ShaderEngine(ctx)
        used = {layer.preset for layer in DEFAULT_LAYERS}
        assert set(engine.programs.keys()) == used
        assert set(engine.vaos.keys()) == used
    finally:
        ctx.release()


def test_engine_render_produces_nonblack_output() -> None:
    """Render to an offscreen FBO; verify at least one pixel is lit."""
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

        features = FastFeatures(
            rms=[0.5] * 14,
            peak=[0.5] * 14,
            centroid=[100.0 + i * 800.0 for i in range(14)],
            onset_envelope=[0.8] * 14,
            n_channels=14,
        )
        engine.render(features, time_s=1.0, resolution=size)

        raw = fbo.read(components=4, dtype="f1")
        assert any(b > 0 for b in raw), "render produced an all-black framebuffer"
    finally:
        ctx.release()


@pytest.mark.parametrize("preset", PRESETS)
def test_each_shader_renders_nonblack_when_driven(preset: str) -> None:
    """Each preset, fed audible RMS + a centroid + an onset envelope,
    must produce visible output."""
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


def test_engine_render_with_zero_channel_weights_is_black() -> None:
    """When all channel weights are 0, every layer's u_channel_weight is
    zero, so shaders multiply to nothing → frame is solid black."""
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
        state = VisualState(channel_weight=[0.0] * 14)
        engine.render(features, time_s=1.0, resolution=size, state=state)

        raw = fbo.read(components=4, dtype="f1")
        for i in range(0, len(raw), 4):
            assert raw[i] == 0, f"R != 0 at pixel {i // 4}"
            assert raw[i + 1] == 0, f"G != 0 at pixel {i // 4}"
            assert raw[i + 2] == 0, f"B != 0 at pixel {i // 4}"
    finally:
        ctx.release()


# --------------------------------------------------------------------------- #
# Compositor (post-FX pass)
# --------------------------------------------------------------------------- #


def _composite_setup(ctx, size=(64, 64)):
    """Helper: build a Compositor + offscreen FBO + output FBO.

    Caller paints whatever they want into `comp._shader_tex` (the
    backing colour texture of the offscreen FBO) — usually a regional
    pattern via numpy + texture.write so we have something asymmetric
    for the post-FX to act on.
    """
    from apophenia.visuals.shader_engine import Compositor

    comp = Compositor(ctx)
    comp.offscreen_fbo(size)  # sizes the internal _shader_tex

    out_tex = ctx.texture(size, components=4, dtype="f1")
    out_fbo = ctx.framebuffer(color_attachments=[out_tex])
    return comp, out_fbo, size


def _paint_offscreen(comp, rgba_bytes: bytes) -> None:
    """Write a precomputed RGBA byte buffer into the offscreen FBO's
    backing texture. Bypasses the GLSL path so tests can set up exact
    pixel patterns without needing a helper shader."""
    assert comp._shader_tex is not None
    comp._shader_tex.write(rgba_bytes)


def _read_pixel(fbo, size, x, y):
    raw = fbo.read(components=4, dtype="f1")
    idx = (y * size[0] + x) * 4
    return raw[idx], raw[idx + 1], raw[idx + 2]


def test_compositor_passes_through_shader_color_at_neutral_settings() -> None:
    """All FX neutral → composite output should equal the offscreen FBO
    contents (within rounding)."""
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (32, 32)
        fbo = comp.offscreen_fbo(size)

        fbo.use()
        ctx.clear(1.0, 0.0, 0.0, 1.0)
        ctx.viewport = (0, 0, *size)

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        assert raw[idx] >= 240, f"R should be ~255 at centre, got {raw[idx]}"
        assert raw[idx + 1] <= 15, f"G should be ~0 at centre, got {raw[idx + 1]}"
        assert raw[idx + 2] <= 15, f"B should be ~0 at centre, got {raw[idx + 2]}"
    finally:
        ctx.release()


def test_compositor_bloom_zero_is_identity() -> None:
    """bloom=0 should give the same output as bloom=0.0 (the implicit
    default for tests that don't pass it)."""
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (32, 32)
        fbo = comp.offscreen_fbo(size)
        fbo.use()
        ctx.clear(0.5, 0.2, 0.7, 1.0)
        ctx.viewport = (0, 0, *size)

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])

        # Baseline render with no bloom.
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, bloom=0.0)
        raw_base = out_fbo.read(components=4, dtype="f1")

        # Re-paint base + render again with explicit bloom=0.0.
        fbo.use()
        ctx.clear(0.5, 0.2, 0.7, 1.0)
        ctx.viewport = (0, 0, *size)
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, bloom=0.0)
        raw_again = out_fbo.read(components=4, dtype="f1")

        # Should be byte-identical.
        assert bytes(raw_base) == bytes(raw_again)
    finally:
        ctx.release()


def test_compositor_bloom_brightens_dark_region_near_bright_one() -> None:
    """A half-and-half image (left bright, right dark) should bleed
    bright into dark when bloom is on. Pixels well into the dark side
    pick up a non-trivial glow that wasn't there at bloom=0."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (128, 128)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        # Left half white, right half black.
        img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
        img[:, : size[0] // 2] = [255, 255, 255, 255]
        img[:, size[0] // 2 :, 3] = 255
        _paint_offscreen(comp, img.tobytes())

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, bloom=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        # Re-paint (mipmaps may have been overwritten by previous render).
        _paint_offscreen(comp, img.tobytes())
        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, bloom=1.0)
        raw_bloom = out_fbo.read(components=4, dtype="f1")

        # Sample a pixel just inside the dark side (10% past the bright
        # boundary, well within the bloom radius). With bloom off it's
        # pitch black; with bloom on it should pick up the glow.
        sample_x = size[0] * 60 // 100  # 60% across; boundary is at 50%
        sample_y = size[1] // 2
        idx = (sample_y * size[0] + sample_x) * 4
        no_lum = max(raw_no[idx], raw_no[idx + 1], raw_no[idx + 2])
        bloom_lum = max(raw_bloom[idx], raw_bloom[idx + 1], raw_bloom[idx + 2])
        assert no_lum < 20, f"baseline should be near-black, got {no_lum}"
        # Bloom is intentionally tasteful (not a washout). A faint but
        # measurable glow is the right shape — anything > +12 over
        # baseline confirms light is actually spreading from the bright
        # side into the dark. Real saturated shaders bloom much more.
        assert bloom_lum > no_lum + 12, (
            f"bloom should brighten dark side; got no={no_lum}, bloom={bloom_lum}"
        )
    finally:
        ctx.release()


def test_compositor_saturation_zero_collapses_to_grey() -> None:
    """saturation=0 must desaturate to luma; R/G/B at centre near-equal."""
    from apophenia.visuals.shader_engine import Compositor

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp = Compositor(ctx)
        size = (16, 16)
        fbo = comp.offscreen_fbo(size)
        fbo.use()
        ctx.clear(0.8, 0.2, 0.4, 1.0)
        ctx.viewport = (0, 0, *size)

        out_tex = ctx.texture(size, components=4, dtype="f1")
        out_fbo = ctx.framebuffer(color_attachments=[out_tex])
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=0.0)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        r, g, b = raw[idx], raw[idx + 1], raw[idx + 2]
        assert abs(r - g) < 5 and abs(g - b) < 5 and abs(r - b) < 5, (
            f"saturation=0 should give grey, got R={r} G={g} B={b}"
        )
    finally:
        ctx.release()


def test_compositor_kaleidoscope_2_segments_left_right_symmetric() -> None:
    """kaleidoscope=2 (180° wedge mirrored) → output symmetric across
    the vertical mid-line."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        comp, out_fbo, size = _composite_setup(ctx, size=(48, 48))

        img = np.zeros((48, 48, 4), dtype=np.uint8)
        img[:, : 48 // 2] = [0, 0, 255, 255]
        img[:, 48 // 2 :] = [0, 255, 0, 255]
        _paint_offscreen(comp, img.tobytes())

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, kaleidoscope_segments=2)

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
        assert matches / total > 0.7, (
            f"kaleidoscope=2 should be ~mirror-symmetric, only {matches}/{total} match"
        )
    finally:
        ctx.release()


def test_compositor_kaleidoscope_1_is_identity() -> None:
    """kaleidoscope=1 must leave UV untouched."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (32, 32)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        img = np.zeros((32, 32, 4), dtype=np.uint8)
        img[:, : 16] = [0, 0, 255, 255]
        img[:, 16:] = [0, 255, 0, 255]
        _paint_offscreen(comp, img.tobytes())

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, kaleidoscope_segments=1)

        r1, g1, b1 = _read_pixel(out_fbo, size, 4, 16)
        r2, g2, b2 = _read_pixel(out_fbo, size, 28, 16)
        assert b1 > 200 and g1 < 60
        assert g2 > 200 and b2 < 60
    finally:
        ctx.release()


def test_compositor_chromatic_separates_rgb_at_edges() -> None:
    """Vertical edge (white left half / black right half) with chromatic=1
    leaks R into the dark side and pulls B out of the bright side."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (96, 16)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        img = np.zeros((16, 96, 4), dtype=np.uint8)
        img[:, : 96 // 2] = [255, 255, 255, 255]
        img[:, 96 // 2 :, 3] = 255
        _paint_offscreen(comp, img.tobytes())

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, chromatic=1.0)
        raw_chrom = out_fbo.read(components=4, dtype="f1")

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, chromatic=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        y = size[1] // 2
        x_just_dark = 96 // 2 + 1
        idx = (y * size[0] + x_just_dark) * 4
        r_chrom = raw_chrom[idx]
        r_no = raw_no[idx]
        assert r_chrom > r_no + 30, (
            f"red should leak into dark side; got R={r_chrom} (chrom) vs R={r_no} (no chrom)"
        )

        x_just_bright = 96 // 2 - 2
        idx2 = (y * size[0] + x_just_bright) * 4
        b_chrom = raw_chrom[idx2 + 2]
        b_no = raw_no[idx2 + 2]
        assert b_chrom < b_no - 30, (
            f"blue should leak out of bright side; got B={b_chrom} (chrom) vs B={b_no} (no chrom)"
        )
    finally:
        ctx.release()


def test_compositor_trail_zero_does_not_persist() -> None:
    """trail=0 means feedback is ignored — bright pixels in frame N
    must NOT bleed into frame N+1's output."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (32, 32)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        # Frame 1: paint offscreen white, render with trail=0.
        white = np.full((32, 32, 4), 255, dtype=np.uint8)
        _paint_offscreen(comp, white.tobytes())
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, trail=0.0)

        # Frame 2: paint offscreen black, render with trail=0.
        # Output should be black — no persistence from frame 1.
        black = np.zeros((32, 32, 4), dtype=np.uint8)
        black[..., 3] = 255
        _paint_offscreen(comp, black.tobytes())
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, trail=0.0)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        assert raw[idx] <= 5, f"trail=0 should not persist; R={raw[idx]}"
        assert raw[idx + 1] <= 5, f"trail=0 should not persist; G={raw[idx + 1]}"
        assert raw[idx + 2] <= 5, f"trail=0 should not persist; B={raw[idx + 2]}"
    finally:
        ctx.release()


def test_compositor_trail_persists_bright_pixels() -> None:
    """trail=0.85 means yesterday's bright pixels still glow today.
    Frame 1 paints white; frame 2 paints black; with trail on the
    output of frame 2 should still show appreciable brightness."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (32, 32)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        # Frame 1: paint white, render with trail on (warms up feedback).
        white = np.full((32, 32, 4), 255, dtype=np.uint8)
        _paint_offscreen(comp, white.tobytes())
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, trail=0.85)

        # Frame 2: paint black, but trail keeps prev-frame's white glowing.
        black = np.zeros((32, 32, 4), dtype=np.uint8)
        black[..., 3] = 255
        _paint_offscreen(comp, black.tobytes())
        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, trail=0.85)

        raw = out_fbo.read(components=4, dtype="f1")
        cx, cy = size[0] // 2, size[1] // 2
        idx = (cy * size[0] + cx) * 4
        # Trail decay 0.85 over 1 frame: expect ≥ 200 (out of 255).
        avg_lum = (raw[idx] + raw[idx + 1] + raw[idx + 2]) // 3
        assert avg_lum > 150, (
            f"trail=0.85 should persist white pixels into next frame; "
            f"got avg luma {avg_lum}"
        )
    finally:
        ctx.release()


def test_compositor_glitch_displaces_some_rows() -> None:
    """Glitch=1 row-displacement: output differs from glitch=0 across
    many pixels (the hash trips ~15% of rows)."""
    import numpy as np

    ctx = _try_make_ctx()
    if ctx is None:
        pytest.skip("no GL context available")
    try:
        size = (64, 64)
        comp, out_fbo, _ = _composite_setup(ctx, size=size)

        img = np.zeros((64, 64, 4), dtype=np.uint8)
        img[:, : 32] = [255, 0, 0, 255]
        img[:, 32:] = [0, 255, 0, 255]
        _paint_offscreen(comp, img.tobytes())

        out_fbo.use()
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, glitch=1.0, time_s=0.0)
        raw_glitch = out_fbo.read(components=4, dtype="f1")

        out_fbo.use()
        ctx.clear(0, 0, 0, 1)
        ctx.viewport = (0, 0, *size)
        comp.render(saturation=1.0, glitch=0.0, time_s=0.0)
        raw_no = out_fbo.read(components=4, dtype="f1")

        diff = sum(
            1 for i in range(0, len(raw_glitch), 4)
            if abs(raw_glitch[i] - raw_no[i]) > 50
            or abs(raw_glitch[i + 1] - raw_no[i + 1]) > 50
        )
        assert diff > 20, f"glitch should displace many pixels; got diff count {diff}"
    finally:
        ctx.release()
