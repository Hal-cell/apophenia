#version 330

// PARTICLE RENDER (fragment stage) — soft circular sprite per particle.
// `gl_PointCoord` runs [0,1]² across the point sprite; we draw a
// gaussian-ish glow with HSV→RGB colouring driven by the channel's
// spectral centroid (passed through from the vertex stage).

uniform float u_hue_offset_deg;  // state.palette.hue * 360 — global rotation
uniform float u_saturation;       // state.palette.saturation

in float v_age_norm;
in float v_hue_deg;
in float v_intensity;

out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Distance from sprite centre in [0, ~0.71].
    vec2 d = gl_PointCoord - 0.5;
    float r = length(d);
    if (r > 0.5) discard;

    // Soft falloff: bright at centre, fades to zero at edge.
    float glow = exp(-r * r * 18.0);

    // Apply global hue rotation from palette.hue.
    float hue = mod(v_hue_deg + u_hue_offset_deg, 360.0) / 360.0;
    // Saturation can pump above 1 for over-saturation; clamp at HSV's
    // accepted range. (We pass S directly to hsv2rgb which expects [0,1].)
    float s = clamp(u_saturation * 0.7, 0.0, 1.0);

    vec3 color = hsv2rgb(vec3(hue, s, 1.0)) * glow * v_intensity;
    fragColor = vec4(color, glow * v_intensity);
}
