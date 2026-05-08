#version 330

// NOISE_SWEEP — value-noise field that scrolls horizontally, with
// brightness modulated by RMS. Atmospheric / FX feel. Sums layers
// of noise (cheap fbm) so it has a bit of cloud-like structure.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
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

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float amp = 0.5;
    for (int i = 0; i < 3; i++) {
        v += amp * noise(p);
        p *= 2.07;
        amp *= 0.5;
    }
    return v;
}

void main() {
    vec2 uv = v_uv;
    uv.x *= u_resolution.x / u_resolution.y;

    // Each channel gets its own scroll direction + scale to avoid
    // visual clash across channels.
    float c = u_channel;
    vec2 dir = vec2(cos(c * 0.5), sin(c * 0.5));
    vec2 p   = uv * (3.0 + c * 0.2) + dir * u_time * 0.15;

    float n = fbm(p);
    // Stretch contrast a bit so the noise reads as patches not flat grey.
    n = smoothstep(0.35, 0.85, n);

    float intensity = n * u_rms * u_channel_weight;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.6, 0.95)) * intensity;
    fragColor = vec4(color, intensity * 0.55);
}
