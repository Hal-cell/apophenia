#version 330

// COMPOSITOR — final post-FX stage applied to the shader-engine output.
//
// Phase 14 pipeline (per pixel):
//   v_uv → kaleidoscope wedge fold → glitch row displacement →
//   sample shader_tex with chromatic per-channel UV offsets →
//   pyramid bloom (24-tap Gaussian over mipmap level 2 of shader_tex,
//                 high-pass-thresholded per sample) →
//   saturation →
//   max-decay blend with previous-frame composite output (feedback /
//                 trail). At trail=0 this is a no-op; at trail=0.85
//                 the trail decays over ~5s and bright pixels leave
//                 long ghosting tails.
//
// The feedback path runs in screen-space (no kaleidoscope / glitch
// applied to the previous-frame sample) so trails follow the picture
// even as the kaleidoscope geometry shifts. Combined via per-channel
// max so bright pixels persist (long-exposure-photograph feel) while
// dim regions still update from the new shader content.

uniform sampler2D u_shader_tex;
uniform sampler2D u_feedback_tex;
uniform float     u_glitch;
uniform float     u_chromatic;
uniform int       u_kaleidoscope_segments;
uniform float     u_saturation;
uniform float     u_bloom;
uniform float     u_trail;
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

vec3 bloom_sample(vec2 uv, float strength) {
    if (strength <= 0.0) return vec3(0.0);

    const int N = 24;
    const vec2 OFFS[24] = vec2[24](
        vec2( 0.000,  0.000),
        vec2( 0.040,  0.000), vec2(-0.040,  0.000),
        vec2( 0.000,  0.040), vec2( 0.000, -0.040),
        vec2( 0.028,  0.028), vec2(-0.028,  0.028),
        vec2( 0.028, -0.028), vec2(-0.028, -0.028),
        vec2( 0.080,  0.000), vec2(-0.080,  0.000),
        vec2( 0.000,  0.080), vec2( 0.000, -0.080),
        vec2( 0.057,  0.057), vec2(-0.057,  0.057),
        vec2( 0.057, -0.057), vec2(-0.057, -0.057),
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

    vec3 sum = vec3(0.0);
    for (int i = 0; i < N; i++) {
        vec3 c = textureLod(u_shader_tex, uv + OFFS[i], 2.0).rgb;
        float l = dot(c, vec3(0.299, 0.587, 0.114));
        float gate = smoothstep(0.15, 0.55, l);
        sum += c * gate * W[i];
    }
    return sum * strength * 2.4;
}

void main() {
    vec2 uv = kaleidoscope(v_uv, u_kaleidoscope_segments);
    uv = glitch_uv(uv, u_glitch, u_time);

    // Chromatic split + base sample.
    float aberr = u_chromatic * 0.012;
    float r = texture(u_shader_tex, uv + vec2(-aberr, 0.0)).r;
    vec3  g = texture(u_shader_tex, uv).rgb;
    float b = texture(u_shader_tex, uv + vec2( aberr, 0.0)).b;
    vec3 base = vec3(r, g.g, b);

    base += bloom_sample(uv, u_bloom);
    base = apply_saturation(base, u_saturation);

    // Feedback / trail: max-decay blend with last frame's composite.
    // Sampled at v_uv (the un-warped UV) so trails are screen-stable
    // — kaleidoscope only mirrors the new shader content, not the
    // historical exposure.
    if (u_trail > 0.0) {
        vec3 prev = texture(u_feedback_tex, v_uv).rgb * u_trail;
        // Per-channel max gives "long-exposure photograph" persistence
        // — bright pixels linger and decay; dim regions update from
        // the fresh shader content immediately. Plain additive would
        // saturate to white quickly; mix() blend would dim the new
        // content. Max-decay is the right operator for visual trails.
        base = max(base, prev);
    }

    fragColor = vec4(base, 1.0);
}
