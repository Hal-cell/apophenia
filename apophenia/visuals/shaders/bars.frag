#version 330

// BARS — a vertical-bar pseudo-spectrum. Bars are positioned at
// hashed x-coords (deterministic per-channel) and grow upward with
// RMS, with extra height on onset. Best for percussive content.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_onset;
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
    vec2 uv = v_uv;  // [0, 1] both axes

    // 24 columns; each channel claims a couple via a hash so multiple
    // bars-channels don't clobber the same bar.
    float n_bars = 24.0;
    float col = floor(uv.x * n_bars);
    float c = u_channel;
    float seed = fract(sin(col * 12.9898 + c * 3.7) * 43758.5453);

    // Mask: only this channel's bars are bright. Use a per-bar/
    // per-channel hash filter.
    float own_bar = step(fract(seed * 5.7), 0.18 + 0.05 * c);

    float bar_height =
        own_bar * (0.05 + (u_rms + u_onset * 0.5) * (0.3 + 0.7 * seed));

    float in_bar  = step(uv.y, bar_height);
    // Slim each bar a little so neighbours stay visually distinct.
    float in_col  = step(fract(uv.x * n_bars), 0.7);

    float intensity = in_bar * in_col * u_channel_weight;
    vec3  color = hsv2rgb(vec3(u_hue / 360.0, 0.7, 1.0));
    fragColor = vec4(color * intensity, intensity * 0.9);
}
