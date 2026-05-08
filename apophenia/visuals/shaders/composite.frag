#version 330

// COMPOSITOR — final stage that blends shader-engine output with the
// AI texture, applies post-FX, and writes to the visible window.
//
// Pipeline (per-pixel):
//   1. start with v_uv ∈ [0, 1]²
//   2. KALEIDOSCOPE (radial mirror) when segments > 1
//   3. GLITCH (horizontal block displacement) scaled by u_glitch
//   4. sample shader_tex at the warped UV
//   5. sample BOTH ai textures (prev + current) and crossfade by
//      u_ai_interp ∈ [0, 1] — gives us smooth motion between SDXL gens
//      without the strobe-cut feel of raw frame swaps at 5–15 fps
//   6. mix(shader, ai) by u_blend (with u_has_ai gating)
//   7. CHROMATIC aberration: re-sample R/B at small UV offsets, keep
//      G centred — yields the classic lens fringe
//   8. saturation
//
// Inputs:
//   u_shader_tex             - offscreen FBO from ShaderEngine
//   u_ai_tex_prev            - previous AI frame (for time interpolation)
//   u_ai_tex_cur             - current AI frame
//   u_blend                  - state.blend.shader_ai ∈ [0, 1]
//   u_has_ai                 - 0/1; gates blend so warmup shows shader
//   u_ai_interp              - [0, 1]; 0 = prev, 1 = current; updated
//                              per render frame from wallclock
//   u_glitch                 - state.fx.glitch ∈ [0, 1]
//   u_chromatic              - state.fx.chromatic ∈ [0, 1]
//   u_kaleidoscope_segments  - state.fx.kaleidoscope ∈ [1, 12] (int);
//                              1 = identity, ≥2 enables fold
//   u_saturation             - state.palette.saturation ∈ [0, 2]
//   u_time                   - render-frame wallclock seconds; drives
//                              glitch's per-row hash so it animates

uniform sampler2D u_shader_tex;
uniform sampler2D u_ai_tex_prev;
uniform sampler2D u_ai_tex_cur;
uniform float     u_blend;
uniform float     u_has_ai;
uniform float     u_ai_interp;
uniform float     u_glitch;
uniform float     u_chromatic;
uniform int       u_kaleidoscope_segments;
uniform float     u_saturation;
uniform float     u_time;

in  vec2 v_uv;
out vec4 fragColor;

// ----- Helpers ----- //

float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

vec2 kaleidoscope(vec2 uv, int segments) {
    if (segments <= 1) return uv;
    // Centre on (0.5, 0.5); compute polar coords.
    vec2 p = uv - 0.5;
    float r = length(p);
    float a = atan(p.y, p.x);
    // Wedge size in radians.
    float wedge = 6.283185307179586 / float(segments);
    // Wrap to one wedge, then mirror across its centre line — the mirror
    // is what makes it kaleidoscopic instead of just rotational.
    a = mod(a, wedge);
    a = abs(a - wedge * 0.5);
    return vec2(cos(a), sin(a)) * r + 0.5;
}

vec2 glitch_uv(vec2 uv, float intensity, float t) {
    if (intensity <= 0.0) return uv;
    // Quantise to ~40 horizontal "scanlines"; per-line hash gives a
    // chunky block displacement that animates over time.
    float row = floor(uv.y * 40.0);
    float h = hash11(row + floor(t * 8.0) * 0.137);
    // Map [0, 1] → [-1, 1] then scale by intensity * 0.06 (≈ 6% screen
    // width at full intensity). Threshold so most rows aren't displaced.
    float displaced = (h > 0.85) ? (h * 2.0 - 1.0) : 0.0;
    return vec2(uv.x + displaced * intensity * 0.06, uv.y);
}

vec3 sample_full(vec2 uv) {
    // Sample both AI textures and crossfade.
    vec3 ai_prev = texture(u_ai_tex_prev, uv).rgb;
    vec3 ai_cur  = texture(u_ai_tex_cur,  uv).rgb;
    vec3 ai = mix(ai_prev, ai_cur, clamp(u_ai_interp, 0.0, 1.0));

    vec3 shader_rgb = texture(u_shader_tex, uv).rgb;
    return mix(shader_rgb, ai, u_blend * u_has_ai);
}

vec3 apply_saturation(vec3 rgb, float s) {
    float luma = dot(rgb, vec3(0.299, 0.587, 0.114));
    return mix(vec3(luma), rgb, s);
}

void main() {
    // 1. start with v_uv
    // 2. kaleidoscope
    vec2 uv = kaleidoscope(v_uv, u_kaleidoscope_segments);
    // 3. glitch
    uv = glitch_uv(uv, u_glitch, u_time);

    // 4-6. sample with chromatic split: re-sample R / B with horizontal
    //      offset; G stays centred. Aberration scales with intensity.
    float aberr = u_chromatic * 0.012;
    vec3 base   = sample_full(uv);
    vec3 base_r = sample_full(uv + vec2(-aberr, 0.0));
    vec3 base_b = sample_full(uv + vec2( aberr, 0.0));
    vec3 mixed  = vec3(base_r.r, base.g, base_b.b);

    // 7. saturation
    mixed = apply_saturation(mixed, u_saturation);

    fragColor = vec4(mixed, 1.0);
}
