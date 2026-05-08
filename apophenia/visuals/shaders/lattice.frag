#version 330

// LATTICE — animated voronoi cells. Cell anchors drift on a sin/cos
// rhythm so the lattice breathes; centroid controls cell density (high
// freq = fine grain); RMS modulates cell brightness; onset highlights
// the cell *edges* so a hit reads as a network flash rather than a
// brightness pump.
//
// 3×3 voronoi neighbourhood × 1 hash + 1 sin per cell = ~120 ALU/pixel,
// the heaviest of the five. Still fine at 14 layers @ 1080p (the M3 Max
// GPU has plenty of headroom).

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

vec2 hash22(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)),
             dot(p, vec2(269.5, 183.3)));
    return fract(sin(p) * 43758.5453);
}

// Returns vec2(d1, d2): distances to the nearest two cell anchors.
// Edge proximity is then `d2 - d1` — small near a cell wall, large
// inside a cell.
vec2 voronoi(vec2 p, float t) {
    vec2 g = floor(p);
    vec2 f = fract(p);
    float d1 = 1e9, d2 = 1e9;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 cell = vec2(x, y);
            vec2 jitter = hash22(g + cell);
            // Drift each cell anchor in a unit-circle orbit using its
            // hash as a phase offset — gives the lattice its "breathing".
            jitter = 0.5 + 0.5 * sin(t + 6.2832 * jitter);
            vec2 r = cell + jitter - f;
            float d = dot(r, r);
            if (d < d1) { d2 = d1; d1 = d; }
            else if (d < d2) { d2 = d; }
        }
    }
    return vec2(sqrt(d1), sqrt(d2));
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Per-channel offset — keeps the lattices from co-aligning.
    vec2 offset = vec2(sin(u_channel * 0.7) * 0.5,
                       cos(u_channel * 1.1) * 0.35);

    // Density: bass = chunky cells, treble = fine grid.
    float density = 3.0 + clamp(u_centroid, 0.0, 12000.0) / 1500.0;
    vec2 p = (uv - offset) * density;

    vec2 v = voronoi(p, u_time * 0.55);
    float edge = v.y - v.x;  // distance to the nearest cell wall

    // Cell body: filled where we're far from a wall.
    float body = smoothstep(0.06, 0.0, edge);

    // Edge highlight: thin bright band along the walls; onset spikes it.
    float edge_band = (1.0 - smoothstep(0.0, 0.04, edge));

    // Soft global falloff.
    float d = length(uv - offset);
    float falloff = exp(-d * d * 1.0);

    float intensity = (body * u_rms * 0.55 + edge_band * u_onset * 1.6)
                      * u_channel_weight * falloff;

    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.65, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.75);
}
