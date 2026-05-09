#version 330

// REACTION — visual rendering of the Gray-Scott simulation texture.
//
// Reads (U, V) from `u_sim_tex` (managed by ReactionDiffusion at 256²,
// sampled here at full screen resolution via bilinear filter) and
// renders the activator concentration V as the visible pattern. U is
// used as an auxiliary darkening term — areas with U near 1 (substrate
// untouched) are kept faint, areas where U has been consumed (reaction
// active) are bright.
//
// Audio coupling:
//   * RMS modulates overall intensity — louder audio reads as brighter
//     pattern. The simulation itself is autonomous; audio doesn't
//     perturb it (yet — that's a phase-16+ idea). Sound just
//     amplifies / dims the existing pattern.
//   * Centroid maps to hue (warm = bassy, cool = bright) like the
//     other layer presets.
//   * Onset adds a brief brightening flash so beats register on the
//     pattern even if the pattern itself is slow to evolve.
//
// Per-channel sampling: each channel reads the *same* simulation
// texture (it's global) but applies its own UV offset, so multiple
// channels render the pattern from different "viewports" of the sim.
// Stacking them additively across channels gives a kind of multi-
// exposure look on the same underlying chemistry.

uniform sampler2D u_sim_tex;       // bound by ShaderEngine.render
uniform vec2      u_resolution;
uniform float     u_rms;
uniform float     u_centroid;
uniform float     u_onset;
uniform float     u_hue;
uniform float     u_channel_weight;
uniform float     u_channel;

in  vec2 v_uv;
out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 uv = v_uv;

    // Per-channel UV transform: zoom + offset + slight rotation. Each
    // layer instance reads a different "window" into the simulation.
    float angle = u_channel * 0.41;  // small per-channel rotation
    float zoom = 0.6 + mod(u_channel * 0.137, 1.0) * 0.6;
    vec2 centre = vec2(
        sin(u_channel * 1.7) * 0.18 + 0.5,
        cos(u_channel * 2.3) * 0.18 + 0.5
    );
    vec2 p = uv - centre;
    float c = cos(angle), s = sin(angle);
    p = mat2(c, -s, s, c) * p / zoom;
    vec2 sim_uv = p + 0.5;

    // Sample the chemistry. V is the activator (the visible pattern),
    // U is the substrate (full where reaction hasn't fired yet).
    vec2 chem = texture(u_sim_tex, sim_uv).rg;
    float u = chem.x;
    float v = chem.y;

    // The reaction "edges" — where V is non-zero but the substrate U
    // is being consumed — are where the pattern is most dynamic.
    // Combine V with (1 - U) for a high-contrast read of the active
    // reaction zones.
    float pattern = max(v, 1.0 - u) * v;
    pattern = smoothstep(0.05, 0.55, pattern);

    // Onset adds a brief brightening so beats register on slow patterns.
    pattern += u_onset * 0.25 * pattern;

    // Soft falloff so each instance attenuates at the edges of its
    // rotated window — keeps the layer compositing tidy.
    float r = length(uv - vec2(0.5));
    float falloff = exp(-r * r * 0.6);

    float intensity = pattern * u_rms * u_channel_weight * falloff * 1.5;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.7, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
