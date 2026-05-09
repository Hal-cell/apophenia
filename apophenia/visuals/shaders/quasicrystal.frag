#version 330

// QUASICRYSTAL — sum of N cosine plane waves whose directions are
// stepped by the golden angle (≈ 137.508°, 2π·(1−1/φ) radians).
//
// Maths: a quasicrystal interference pattern is
//   I(p) = Σᵢ cos(p·dᵢ + φ)         where dᵢ = (cos θᵢ, sin θᵢ)
//                                      θᵢ = i · 2π(1−1/φ)
// When N divides 2π evenly the result is periodic (a regular grid);
// when the angle increment is *irrational* in 2π (golden angle is the
// canonical choice) the resulting pattern has perfect rotational
// symmetry of order ∞ but **no translational symmetry** — which is
// the formal definition of a 2D quasicrystal. Visually you get
// Penrose-tile-flavoured aperiodic geometry with long-range order.
//
// Centroid → wave count (5..11). Bassy channels read as 5-fold
// pentagonal lattices; bright channels approach an isotropic dot
// pattern. RMS sharpens the contrast curve so quiet sections are
// soft interference washes and loud sections are hard tile edges.
// Onset shifts the global phase so every hit "rotates" the lattice.
//
// Cost: at most 11 cosines + a pow + falloff. ~80 ALU/pixel — cheap.

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

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    vec2 centre = vec2(sin(u_channel * 0.83) * 0.45,
                       cos(u_channel * 1.27) * 0.35);
    // Lattice spacing scales with centroid: bassy channels → coarse
    // tiling, bright channels → fine grain. Multiplier picked so that
    // at midpoint we see ~6-8 wavelengths across the falloff radius.
    float scale = 4.0 + clamp(u_centroid, 0.0, 12000.0) / 1500.0;
    vec2 p = (uv - centre) * scale;

    // Wave count from centroid: 5 (pentagonal) → 11 (near-isotropic).
    int n_waves = 5 + int(clamp(u_centroid / 2000.0, 0.0, 6.0));

    // Phase: slow drift over time + onset bursts.
    float phase = u_time * 0.4 + u_onset * 1.8;

    // Golden angle in radians: 2π · (1 - 1/φ) ≈ 2.39996.
    const float GOLDEN = 2.39996322972866;

    float sum = 0.0;
    // GLSL needs a literal loop bound; cap at 11 and break on n_waves.
    for (int i = 0; i < 11; i++) {
        if (i >= n_waves) break;
        float a = float(i) * GOLDEN;
        vec2 dir = vec2(cos(a), sin(a));
        sum += cos(dot(p, dir) + phase);
    }
    sum /= float(n_waves);
    sum = sum * 0.5 + 0.5;  // remap to [0, 1]

    // Audio sharpens the contrast curve. Quiet → soft interference,
    // loud → hard tile edges. Capped so even at full RMS we don't
    // crush mid-tones to black.
    float contrast = 1.0 + u_rms * 2.0 + u_onset * 1.0;
    sum = pow(sum, contrast);

    // Soft global falloff so the layer self-attenuates at its edges.
    float d = length(uv - centre);
    float falloff = exp(-d * d * 0.8);

    float intensity = sum * u_rms * u_channel_weight * falloff * 1.8;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.8, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
