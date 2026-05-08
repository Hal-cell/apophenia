#version 330

// CIRCLE_PULSE — concentric ring expanding outward from each onset
// trigger. The ring's radius rides on time-since-last-onset; on a
// fresh onset the envelope clamps to 1.0 and the ring restarts at
// centre. Best with kick/snare-like channels.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_onset;          // [0, 1] decaying envelope
uniform float u_hue;
uniform float u_channel_weight;
uniform float u_channel;

in  vec2 v_uv;
out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Each channel ring centred at a unique sub-area.
    float c = u_channel;
    vec2  centre = vec2(sin(c * 0.97), cos(c * 1.31)) * 0.55;
    float r = length(uv - centre);

    // Ring radius animated by time. Onset envelope blends a fresh
    // pulse: when high, the ring lights up brightly across a wide
    // band; when decaying, it narrows.
    float ring_r = mod(u_time * 0.4 + c * 0.3, 1.4) - 0.1;
    float band_w = mix(40.0, 8.0, u_onset);  // narrower when no onset
    float ring   = exp(-pow((r - ring_r) * band_w, 2.0));

    // Onset adds a centred flash bump.
    float flash = u_onset * exp(-r * r * 4.0);

    float intensity = (ring + flash) * (0.3 + 0.7 * u_rms) * u_channel_weight;
    vec3  color = hsv2rgb(vec3(u_hue / 360.0, 0.75, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
