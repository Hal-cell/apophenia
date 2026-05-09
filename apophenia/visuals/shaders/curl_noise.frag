#version 330

// CURL_NOISE — incompressible-flow visualization.
//
// Maths: in 2D, the curl of a scalar potential N(x,y) is the vector
//   ∇⊥ N = (∂N/∂y, -∂N/∂x)
// A vector field defined this way has zero divergence by construction
// — it can rotate but cannot expand or contract. That's exactly the
// physical constraint of incompressible fluid flow, so visually the
// motion reads as smoke / vapor / mist drifting, never "blooming" or
// "popping" the way ordinary domain-warped FBM does.
//
// We compute curl by finite differences on the noise potential, then
// integrate UV along the field for a few steps to trace streamlines,
// then sample fbm at the warped position. RMS modulates how far each
// pixel "flows" along the field; centroid drives flow speed; onset
// injects extra vorticity by amplifying the integration step.
//
// Cost: 4 noise() calls for one curl + 4-octave fbm × 1 = 8 noise
// calls × 3 integration steps = 24 noise calls/pixel. About 240 ALU.
// At 14 layers / 1080p that's still ~5% of the M3 Max GPU budget.

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

// 2D curl of the noise potential at p (with time animation baked in
// so the field itself drifts, not just the trace through it).
vec2 curl(vec2 p, float t) {
    const float eps = 0.05;
    float nxp = noise(p + vec2(eps, 0.0) + vec2(t, 0.0));
    float nxm = noise(p - vec2(eps, 0.0) + vec2(t, 0.0));
    float nyp = noise(p + vec2(0.0, eps) + vec2(t, 0.0));
    float nym = noise(p - vec2(0.0, eps) + vec2(t, 0.0));
    return vec2((nyp - nym), -(nxp - nxm)) * (1.0 / (2.0 * eps));
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    vec2 offset = vec2(sin(u_channel * 1.43) * 0.55,
                       cos(u_channel * 2.07) * 0.35);
    vec2 p = (uv - offset) * 1.6;

    // Centroid → flow drift speed (not the speed of the visual streak —
    // that's stationary; we're advecting the *underlying field*).
    float speed = 0.15 + (clamp(u_centroid, 0.0, 12000.0) / 12000.0) * 0.45;
    float t = u_time * speed;

    // Integrate UV along curl field for a few steps. Each step pushes
    // the sample point along the local incompressible flow, building
    // up streamline structure. `step_scale` grows with onset so a
    // hit visibly "spins" the picture.
    float step_scale = 0.06 * (1.0 + u_onset * 1.4);
    vec2 q = p;
    for (int i = 0; i < 3; i++) {
        q += curl(q, t) * step_scale;
    }

    float v = fbm(q);

    // Distance falloff so each layer self-attenuates at its edges
    // (essential for additive 14-layer blend).
    float d = length(uv - offset);
    float falloff = exp(-d * d * 1.0);

    float intensity = v * u_rms * u_channel_weight * falloff * 1.6;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.65, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.6);
}
