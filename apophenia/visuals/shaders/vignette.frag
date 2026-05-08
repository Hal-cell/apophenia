#version 330

// VIGNETTE — soft radial blob centred on screen, hue from centroid,
// brightness from RMS. Quietest of the five presets; meant as a
// background wash for pad-style channels.

uniform vec2  u_resolution;
uniform float u_rms;
uniform float u_hue;            // degrees, mapped from centroid
uniform float u_channel_weight; // [0, 1] mute control
uniform float u_channel;        // for procedural variation

in  vec2 v_uv;
out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Centred coords with aspect correction.
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Each channel's vignette is offset slightly so they don't all
    // pile up at the centre. Deterministic per-channel.
    float c = u_channel;
    vec2  centre = vec2(
        sin(c * 1.7) * 0.4,
        cos(c * 2.3) * 0.25
    );
    float r = length(uv - centre);
    // Soft falloff. At r=0 it's full intensity; gone by r=1.5.
    float blob = exp(-r * r * 1.5);

    float intensity = u_rms * u_channel_weight * blob;
    vec3  color = hsv2rgb(vec3(u_hue / 360.0, 0.55, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.6);
}
