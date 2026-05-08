#version 330

// FLOW — domain-warped FBM noise field. Each channel gets its own
// spatial offset so the 14 layers don't all pile up in the centre.
// RMS scales overall amplitude; centroid drives flow speed (high freq
// = fast, bassy = slow drift); onset injects extra turbulence so a
// sharp hit makes the mist roil.
//
// Cost: 4-octave fbm × 2 (domain warp samples) + 1 final fbm = 9
// noise() calls per pixel. ~100 ALU; fine at 14 layers @ 1080p.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_centroid;
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

float hash21(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hash21(i),                hash21(i + vec2(1.0, 0.0)), f.x),
        mix(hash21(i + vec2(0.0,1.0)),hash21(i + vec2(1.0, 1.0)), f.x),
        f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float amp = 0.5;
    for (int i = 0; i < 4; i++) {
        v += amp * noise(p);
        p *= 2.0;
        amp *= 0.5;
    }
    return v;
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Per-channel anchor — keeps the 14 layers from overlapping at centre.
    vec2 offset = vec2(sin(u_channel * 1.7) * 0.55,
                       cos(u_channel * 2.3) * 0.35);

    vec2 p = (uv - offset) * 1.8;

    // Centroid → flow speed. 50Hz≈0.2; 12kHz≈0.8.
    float speed = 0.2 + (clamp(u_centroid, 0.0, 12000.0) / 12000.0) * 0.6;
    float t = u_time * speed;

    // Domain-warp: read fbm twice at offset positions, use those as
    // displacements for the final sample. Gives an organic stretchy flow.
    vec2 q = vec2(fbm(p + vec2(t,        t * 0.7)),
                  fbm(p + vec2(5.2 - t,  1.3 + t * 0.5)));

    // Onset injects extra warp magnitude — sharp hits = roiling turbulence.
    q *= 1.0 + u_onset * 1.6;

    float v = fbm(p + q * 1.5);

    // Distance falloff so each layer self-attenuates at its edges
    // (essential for additive 14-layer blend).
    float d = length(uv - offset);
    float falloff = exp(-d * d * 1.1);

    float intensity = v * u_rms * u_channel_weight * falloff * 1.4;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.7, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.6);
}
