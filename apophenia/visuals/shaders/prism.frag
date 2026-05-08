#version 330

// PRISM — rotating polygon SDF, hard-edged colored shards.
// Each channel owns one polygon; centroid controls facet count
// (3 = triangle, ~10 = decagon); RMS scales radius; onset spikes
// rotation speed for a frame so a hit reads as a spin kick.
//
// Geometry-only shader — no noise — so it's the cheapest of the five
// (~40 ALU/pixel). Pairs well with flow.frag's organic surfaces.

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

// SDF of a regular n-gon centred at origin with circumradius `r`.
// Standard formulation: rotate to nearest wedge, then perpendicular
// distance to that wedge's bounding line.
float sdNgon(vec2 p, float r, int n) {
    float a = atan(p.y, p.x);
    float wedge = 6.283185307179586 / float(n);
    float ai = mod(a + wedge * 0.5, wedge) - wedge * 0.5;
    return length(p) * cos(ai) - r * cos(wedge * 0.5);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Per-channel centre, deterministic but spread.
    vec2 centre = vec2(sin(u_channel * 1.31) * 0.55,
                       cos(u_channel * 1.71) * 0.40);

    // Spin: base angular velocity scales with channel index, onset
    // adds an instant kick that decays via the envelope.
    float rot = u_time * (0.30 + u_channel * 0.04) + u_onset * 1.4;
    float c = cos(rot), s = sin(rot);
    vec2 p = uv - centre;
    p = mat2(c, -s, s, c) * p;

    // Facet count from centroid: 3..11. Bassy channels = chunky tris,
    // bright = round-ish high-poly.
    int facets = 3 + int(clamp(u_centroid / 1500.0, 0.0, 8.0));

    // Radius from RMS + a little onset bump.
    float radius = 0.06 + u_rms * 0.30 + u_onset * 0.12;

    float d = sdNgon(p, radius, facets);

    // Two layers: a soft fill inside the polygon and a brighter outline
    // around its edge. The outline width grows slightly with onset so
    // hits "ring" outward.
    float fill = 1.0 - smoothstep(-0.005, 0.005, d);
    float edge_w = 0.012 + u_onset * 0.020;
    float edge = exp(-abs(d) * (1.0 / edge_w));

    float intensity = (fill * 0.45 + edge * 0.7) * u_channel_weight;
    intensity *= 0.6 + u_rms * 0.6;  // overall sound-presence gating

    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.85, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.85);
}
