#version 330

// COMPOSITOR — final post-FX stage applied to the shader-engine output.
//
// Phase 12 pipeline (per pixel):
//   v_uv → kaleidoscope wedge fold → glitch row displacement →
//   sample shader_tex with chromatic per-channel UV offsets →
//   pyramid bloom (sample 3 mipmap levels of shader_tex, threshold
//                 by luma, add the bright-passing portion back) →
//   saturation
//
// Bloom maths: instead of running a separate Gaussian blur pass we
// rely on the texture's mipmap chain — each mip is a 2× downsample
// with a built-in 2×2 box filter, so reading mipmap level L is
// roughly equivalent to a Gaussian blur of radius 2^L. Sampling
// levels 2/4/6 and combining gives a 3-octave pyramid that approximates
// a full-spectrum bloom for ~3 texture lookups (vs. ~25 for a separable
// Gaussian).

uniform sampler2D u_shader_tex;
uniform float     u_glitch;
uniform float     u_chromatic;
uniform int       u_kaleidoscope_segments;
uniform float     u_saturation;
uniform float     u_bloom;
uniform float     u_time;

in  vec2 v_uv;
out vec4 fragColor;

float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

vec2 kaleidoscope(vec2 uv, int segments) {
    if (segments <= 1) return uv;
    vec2 p = uv - 0.5;
    float r = length(p);
    float a = atan(p.y, p.x);
    float wedge = 6.283185307179586 / float(segments);
    a = mod(a, wedge);
    a = abs(a - wedge * 0.5);
    return vec2(cos(a), sin(a)) * r + 0.5;
}

vec2 glitch_uv(vec2 uv, float intensity, float t) {
    if (intensity <= 0.0) return uv;
    float row = floor(uv.y * 40.0);
    float h = hash11(row + floor(t * 8.0) * 0.137);
    float displaced = (h > 0.85) ? (h * 2.0 - 1.0) : 0.0;
    return vec2(uv.x + displaced * intensity * 0.06, uv.y);
}

vec3 apply_saturation(vec3 rgb, float s) {
    float luma = dot(rgb, vec3(0.299, 0.587, 0.114));
    return mix(vec3(luma), rgb, s);
}

// Bloom: 24-tap Poisson-disk-style Gaussian sample of the shader FBO,
// reading from mipmap level 2 (already 4× box-filtered → smoother and
// cheaper than 24 lod-0 taps would be). The taps span three concentric
// rings at UV radii ≈ 0.04 / 0.08 / 0.15 — ≈ 4% / 8% / 15% of screen
// width. Weights follow a rough Gaussian over the ring radii so the
// energy decays with distance.
//
// Soft luma threshold: only pixels brighter than ~0.3 luma contribute.
// Below that we fade out smoothly to avoid a hard cutoff that would
// produce ringing in faint regions.
vec3 bloom_sample(vec2 uv, float strength) {
    if (strength <= 0.0) return vec3(0.0);

    const int N = 24;
    // Pre-tabulated Poisson-disk-ish offsets across 3 concentric rings.
    const vec2 OFFS[24] = vec2[24](
        vec2( 0.000,  0.000),
        // inner ring r ≈ 0.04
        vec2( 0.040,  0.000), vec2(-0.040,  0.000),
        vec2( 0.000,  0.040), vec2( 0.000, -0.040),
        vec2( 0.028,  0.028), vec2(-0.028,  0.028),
        vec2( 0.028, -0.028), vec2(-0.028, -0.028),
        // mid ring r ≈ 0.08
        vec2( 0.080,  0.000), vec2(-0.080,  0.000),
        vec2( 0.000,  0.080), vec2( 0.000, -0.080),
        vec2( 0.057,  0.057), vec2(-0.057,  0.057),
        vec2( 0.057, -0.057), vec2(-0.057, -0.057),
        // outer ring r ≈ 0.15
        vec2( 0.150,  0.000), vec2(-0.150,  0.000),
        vec2( 0.000,  0.150), vec2( 0.000, -0.150),
        vec2( 0.106,  0.106), vec2(-0.106,  0.106),
        vec2( 0.106, -0.106)
    );
    const float W[24] = float[24](
        0.10,
        0.05, 0.05, 0.05, 0.05,
        0.04, 0.04, 0.04, 0.04,
        0.030, 0.030, 0.030, 0.030,
        0.025, 0.025, 0.025, 0.025,
        0.020, 0.020, 0.020, 0.020,
        0.015, 0.015, 0.015
    );

    // Per-sample threshold: each tap contributes only if it's bright
    // enough on its own (otherwise dim neighbours dilute the glow when
    // we average then threshold). This is the high-pass-then-blur
    // ordering that real bloom wants.
    vec3 sum = vec3(0.0);
    for (int i = 0; i < N; i++) {
        vec3 c = textureLod(u_shader_tex, uv + OFFS[i], 2.0).rgb;
        float l = dot(c, vec3(0.299, 0.587, 0.114));
        // Soft per-sample threshold; faint contributions fade smoothly.
        // Tuned permissive (kicks in ~0.15 luma) so layered shaders
        // glow even when individual layers' peak luma is modest.
        float gate = smoothstep(0.15, 0.55, l);
        sum += c * gate * W[i];
    }

    return sum * strength * 2.4;
}

void main() {
    vec2 uv = kaleidoscope(v_uv, u_kaleidoscope_segments);
    uv = glitch_uv(uv, u_glitch, u_time);

    // Chromatic split: re-sample shader_tex at offset UVs for R / B;
    // green stays centred. ~1.2% screen-width offset at full intensity.
    float aberr = u_chromatic * 0.012;
    float r = texture(u_shader_tex, uv + vec2(-aberr, 0.0)).r;
    vec3  g = texture(u_shader_tex, uv).rgb;
    float b = texture(u_shader_tex, uv + vec2( aberr, 0.0)).b;
    vec3 base = vec3(r, g.g, b);

    // Add bloom, sampled at the centre UV so chromatic split doesn't
    // muddy the high-frequency glow.
    base += bloom_sample(uv, u_bloom);

    base = apply_saturation(base, u_saturation);
    fragColor = vec4(base, 1.0);
}
