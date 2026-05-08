#version 330

// PARTICLES — procedural 24-particle field. Each particle is fully
// stateless: its position is a deterministic function of its index,
// channel-seeded hashes, and `u_time`, so we don't need a persistent
// particle buffer (compute shaders aren't available on Apple Silicon
// GL 4.1 anyway). Particles drift outward from a per-channel anchor,
// fade over a fixed lifetime, and get briefly enlarged on each onset.
//
// Audio reactivity:
//   - RMS scales overall opacity (fewer / dimmer particles when quiet)
//   - centroid scales drift speed (bassy = slow, bright = darting)
//   - onset enlarges every particle for one frame (an explosive burst)
//   - u_density gates how many particles activate (sparse → dense)
//
// Cost: 24 particles × per-pixel inner loop ≈ 700 ALU. Use the preset
// for 1–2 of the 14 layers, not all of them.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_centroid;
uniform float u_onset;
uniform float u_hue;
uniform float u_channel_weight;
uniform float u_channel;
uniform float u_density;

in  vec2 v_uv;
out vec4 fragColor;

const int N_PARTICLES = 24;
const float LIFETIME = 1.8;  // seconds; particles loop on this period

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec2 hash22(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)),
             dot(p, vec2(269.5, 183.3)));
    return fract(sin(p) * 43758.5453);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Per-channel anchor — different audio channels emit from different
    // screen positions so the 14 layers don't pile at centre.
    vec2 anchor = vec2(sin(u_channel * 1.13) * 0.45,
                       cos(u_channel * 1.71) * 0.35);

    // Drift speed scales with centroid (high freq = darting particles).
    float speed = 0.25 + clamp(u_centroid, 0.0, 12000.0) / 12000.0 * 0.6;

    float intensity = 0.0;

    for (int i = 0; i < N_PARTICLES; i++) {
        // Two independent hashes per particle: one for trajectory, one
        // for phase / activation gate.
        vec2 h1 = hash22(vec2(float(i) * 31.7, u_channel + 7.0));
        vec2 h2 = hash22(vec2(float(i) * 19.3, u_channel + 13.0));

        // Density gate: lower density → more particles skip.
        // h1.y is uniform in [0, 1]; particles with h1.y > density
        // contribute zero, so the visual count scales smoothly.
        float gate = step(h1.y, 0.15 + u_density * 0.85);
        if (gate < 0.5) continue;

        // Direction (radial-ish, biased outward).
        vec2 dir = normalize(h2 * 2.0 - 1.0);

        // Phase-shifted age — each particle is at a different point in
        // its lifecycle so the swarm reads as a continuous flow rather
        // than synchronised pulses.
        float phase = h1.x * LIFETIME;
        float age = mod(u_time + phase, LIFETIME);
        float life = age / LIFETIME;  // 0 → 1

        // Position: anchor + drift, plus a subtle swirl so particles
        // don't go in perfectly straight lines.
        vec2 pos = anchor + dir * speed * age;
        pos.x += sin(u_time * 1.3 + float(i)) * 0.04;
        pos.y += cos(u_time * 0.9 + float(i) * 0.7) * 0.04;

        // Soft particle: gaussian falloff. Radius shrinks as it ages
        // (so they "evaporate") and momentarily enlarges on onsets.
        float radius = 0.035 * (1.0 - life * 0.6) + u_onset * 0.05;
        float d = length(uv - pos);
        float glow = exp(-d * d / (radius * radius + 0.0005));

        // Fade out over life — bright at birth, dim at death.
        float fade = 1.0 - life * life;
        intensity += glow * fade;
    }

    // Overall scale: RMS gates presence; channel_weight mutes the layer.
    intensity *= u_rms * u_channel_weight * 0.9;

    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.75, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
