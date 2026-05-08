#version 330

// SHOCK — concentric audio-shock waves emanating from each channel's
// anchor point. Three time-shifted wave fronts coexist so a sustained
// hit reads as a layered ripple rather than a single sine. Onset
// triggers a bright radial burst that fades with the envelope.
//
// Pure trig + exp — no noise, no SDF — so the cheapest noise-driven
// look. Reads great at percussion channels (kick / snare / hat).

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

    vec2 centre = vec2(sin(u_channel * 0.93) * 0.55,
                       cos(u_channel * 1.47) * 0.40);
    float r = length(uv - centre);

    // Wave speed scales with centroid — bassy hits send slow rolling
    // pulses, bright hits send fast crackle.
    float t = u_time * (1.5 + clamp(u_centroid, 0.0, 12000.0) / 6000.0);

    // Three interleaved waves with different frequencies + phases.
    float wave1 = sin(r * 22.0 - t * 4.0);
    float wave2 = sin(r * 13.0 - t * 3.0 + u_channel);
    float wave3 = sin(r * 32.0 - t * 5.5 + u_channel * 2.0);

    float w = (wave1 + wave2 * 0.7 + wave3 * 0.5) / 2.2;
    w = w * 0.5 + 0.5;  // remap to [0, 1]

    // Loud → sharp pulses, quiet → soft sine waves. Power curve squashes
    // the mid-values toward the ends as RMS rises.
    w = pow(w, 1.0 + u_rms * 8.0);

    // Onset adds a bright bullseye at the anchor; falls off with r².
    float burst = u_onset * exp(-r * r * 8.0);

    // Soft global falloff so the layer doesn't fill the whole screen.
    float falloff = exp(-r * r * 0.85);

    float intensity = (w * u_rms + burst * 0.85) * u_channel_weight * falloff;

    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.75, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
