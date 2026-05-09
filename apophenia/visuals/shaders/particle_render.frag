#version 330

// PARTICLE RENDER (fragment stage) — line streak gradient.
//
// Phase-16: each "particle" is now a screen-space line drawn from
// tail (v_t = 0, dim) to head (v_t = 1, bright). The fragment runs
// once per pixel along that line, interpolating v_t in [0, 1].
// Brightness ramps along v_t so the streak fades into nothing
// behind the particle's current position — classic motion-blur look.
//
// The transient-flash term and brightness floor from phase 15 are
// retained: silent particles still render dimly (no flicker off);
// recent home-channel onsets get a brief halo via v_flash.

uniform float u_hue_offset_deg;
uniform float u_saturation;

in float v_t;          // 0 = tail (dim), 1 = head (bright)
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
    // Tail-to-head brightness ramp: head at v_t=1 is full brightness,
    // tail at v_t=0 fades to ~10% so the streak has direction. The
    // 0.1 floor at the tail keeps the line visible end-to-end rather
    // than fading completely to black where it would alias against
    // the dark backdrop.
    float ramp = mix(0.1, 1.0, v_t);

    // During a flash, the head puffs up a bit more — extra ramp at
    // v_t=1 only.
    ramp += v_flash * 0.4 * smoothstep(0.6, 1.0, v_t);

    // Hue: channel centroid + global rotation.
    float hue = mod(v_hue_deg + u_hue_offset_deg, 360.0) / 360.0;
    float s = clamp(u_saturation * 0.7, 0.0, 1.0);

    vec3 color = hsv2rgb(vec3(hue, s, 1.0)) * v_intensity * ramp;
    // Alpha tracks brightness so additive blending puts more energy
    // at the head than the tail.
    float alpha = v_intensity * ramp * 0.85;
    fragColor = vec4(color, alpha);
}
