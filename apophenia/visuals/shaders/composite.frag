#version 330

// COMPOSITOR — final post-FX stage applied to the shader-engine output.
//
// Pipeline (per pixel):
//   v_uv → kaleidoscope wedge fold → glitch row displacement →
//   sample shader_tex with chromatic per-channel UV offsets →
//   saturation
//
// Phase 10: this stage no longer mixes an AI-generated texture; the
// SDXL pipeline was removed. Whatever the shader engine drew into the
// offscreen FBO is what gets warped + recoloured here.

uniform sampler2D u_shader_tex;
uniform float     u_glitch;
uniform float     u_chromatic;
uniform int       u_kaleidoscope_segments;
uniform float     u_saturation;
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
    // Quantise to ~40 horizontal rows; per-row hash gives chunky block
    // displacement that animates over time. Threshold ~85% so most
    // rows pass through cleanly.
    float row = floor(uv.y * 40.0);
    float h = hash11(row + floor(t * 8.0) * 0.137);
    float displaced = (h > 0.85) ? (h * 2.0 - 1.0) : 0.0;
    return vec2(uv.x + displaced * intensity * 0.06, uv.y);
}

vec3 apply_saturation(vec3 rgb, float s) {
    float luma = dot(rgb, vec3(0.299, 0.587, 0.114));
    return mix(vec3(luma), rgb, s);
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
    vec3 mixed = vec3(r, g.g, b);

    mixed = apply_saturation(mixed, u_saturation);
    fragColor = vec4(mixed, 1.0);
}
