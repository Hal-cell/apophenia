#version 330

// PLASMA — slow-flowing FBM blob, the "pad" of the shader presets.
// Smooth lava-lamp texture; RMS sharpens the contrast curve so quiet
// sections stay diffuse and loud ones bloom into hard edges; onset
// adds a transient pulse but the surface motion itself is gentle.
//
// 3 noise samples + a power curve. ~40 ALU/pixel.

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

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    vec2 centre = vec2(sin(u_channel * 0.9) * 0.45,
                       cos(u_channel * 1.4) * 0.30);
    vec2 p = (uv - centre) * 1.6;

    // Three octaves moving at different speeds → plasma flow feel.
    float t = u_time * 0.40;
    float v = 0.0;
    v += noise(p * 1.0 + vec2( t,        t * 0.7));
    v += noise(p * 2.5 + vec2(-t * 1.3,  t * 0.5)) * 0.5;
    v += noise(p * 5.0 + vec2( t * 0.8, -t * 1.1)) * 0.25;
    v /= 1.75;  // back into ~[0, 1]

    // Soft radial mask so each blob is blob-shaped, not a full-screen wash.
    float d = length(uv - centre);
    float blob = exp(-d * d * 1.4);

    // Audio sharpens the contrast: quiet → mush, loud → hard plasma edges.
    // Tuned modestly so even at full RMS/onset the mid-tones don't crush
    // entirely to black (pow base values cluster around 0.5).
    float contrast = 1.0 + u_rms * 1.5 + u_onset * 0.8;
    v = pow(v, contrast);

    float intensity = v * u_rms * u_channel_weight * blob * 2.5;

    // Subtle hue shift driven by the plasma value itself — keeps the
    // texture from being one flat colour.
    float h = mod(u_hue / 360.0 + v * 0.08, 1.0);
    vec3 color = hsv2rgb(vec3(h, 0.6, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.65);
}
