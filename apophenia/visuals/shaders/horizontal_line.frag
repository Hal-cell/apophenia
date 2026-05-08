#version 330

// HORIZONTAL_LINE — a sinusoidal waveform whose amplitude is RMS
// and frequency rises with centroid. Reads as a kind of
// oscilloscope trace per channel. Best for melodic / sustained
// channels (lead, bass).

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_centroid;       // Hz
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

    // Vertical band per channel so multiple horizontal lines don't
    // overlap exactly. Channel n claims a ~0.2-tall slice centred
    // on a y offset that varies per-channel.
    float c = u_channel;
    float y_offset = sin(c * 0.7) * 0.5;

    // Sine wave. Frequency rises with centroid (mapped log-ish).
    float freq = 0.5 + log(max(u_centroid, 50.0) / 50.0) * 1.2;
    float phase = u_time * (1.0 + c * 0.05);
    float wave = sin(uv.x * freq * 6.28 + phase) * u_rms * 0.4;

    // Distance from the line position; gaussian for a soft glow.
    float dist = abs(uv.y - y_offset - wave) / 0.04;
    float line = exp(-dist * dist);

    float intensity = line * u_rms * u_channel_weight;
    vec3  color = hsv2rgb(vec3(u_hue / 360.0, 0.7, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.85);
}
