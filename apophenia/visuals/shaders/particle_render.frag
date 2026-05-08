#version 330

// PARTICLE RENDER (fragment stage) — soft circular sprite per particle.
// `gl_PointCoord` runs [0,1]² across the point sprite; we draw a
// gaussian-ish glow with HSV→RGB colouring driven by the channel's
// spectral centroid (passed through from the vertex stage).
//
// Phase-15 fragment changes: `v_intensity` is now floor-clamped to a
// non-zero base value so particles are always faintly visible (no
// flickering off when a channel goes silent). Transient-flash term
// (`v_flash`) drives a brief brightness bump on onset hits.

uniform float u_hue_offset_deg;  // state.palette.hue * 360 — global rotation
uniform float u_saturation;      // state.palette.saturation

in float v_flash;
in float v_hue_deg;
in float v_intensity;
in float v_speed;

out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 d = gl_PointCoord - 0.5;
    float r = length(d);
    if (r > 0.5) discard;

    // Soft gaussian falloff. Tighter (steeper) when not flashing so
    // ambient particles read as crisp dots; wider during flash so
    // transients have a halo.
    float falloff_strength = mix(22.0, 12.0, v_flash);
    float glow = exp(-r * r * falloff_strength);

    // Hue: channel centroid + global rotation.
    float hue = mod(v_hue_deg + u_hue_offset_deg, 360.0) / 360.0;
    float s = clamp(u_saturation * 0.7, 0.0, 1.0);

    vec3 color = hsv2rgb(vec3(hue, s, 1.0)) * glow * v_intensity;
    fragColor = vec4(color, glow * v_intensity * 0.85);
}
