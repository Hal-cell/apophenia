#version 330

// PARTICLE RENDER (vertex stage) — projects each particle to clip
// space and computes its screen-space size + colour, which the
// fragment stage uses to draw a soft sprite.
//
// Reads the same packed state as `particle_update.vert`. Per-frame
// uniforms: MVP matrix from CameraState + a flat array of per-channel
// hues from spectral centroid + per-channel RMS for size modulation.

uniform mat4  u_mvp;
uniform float u_resolution_y;   // for converting world-space sprite
                                 // size to gl_PointSize
uniform float u_centroid[14];   // Hz; mapped to hue per channel
uniform float u_rms[14];

const int   N_CHANNELS = 14;
const float LIFETIME = 4.0;
const float HUE_LO = 30.0;        // matches centroid_to_hue elsewhere
const float HUE_HI = 200.0;
const float CENTROID_LO = 50.0;
const float CENTROID_HI = 12000.0;

in vec4 in_pos_age;
in vec4 in_vel_seed;

out float v_age_norm;     // [0, 1] — fragment uses this to fade
out float v_hue_deg;      // 0..360 from this particle's channel centroid
out float v_intensity;    // brightness scale at fragment

float centroid_to_hue(float hz) {
    if (hz <= CENTROID_LO) return HUE_LO;
    if (hz >= CENTROID_HI) return HUE_HI;
    float f = (hz - CENTROID_LO) / (CENTROID_HI - CENTROID_LO);
    return HUE_LO + f * (HUE_HI - HUE_LO);
}

void main() {
    vec3 pos = in_pos_age.xyz;
    float age = in_pos_age.w;
    float seed = in_vel_seed.w;

    int my_channel = int(seed * float(N_CHANNELS));
    my_channel = clamp(my_channel, 0, N_CHANNELS - 1);
    float my_rms = u_rms[my_channel];
    float my_centroid = u_centroid[my_channel];

    // Project to clip space.
    gl_Position = u_mvp * vec4(pos, 1.0);

    // Distance from camera in clip space → screen-size scaling. We
    // pull -view.z out of the view-projected position before the
    // perspective divide. gl_Position.w is roughly the view-space
    // distance after a standard perspective projection.
    float depth = max(gl_Position.w, 0.5);

    // Sprite size: modest base, scaled by RMS and inversely by depth.
    // 0.04 world units at depth 1.0 ≈ a few pixels at 1080p.
    float world_size = 0.035 * (0.5 + my_rms * 1.4);
    gl_PointSize = clamp(
        world_size * u_resolution_y / depth,
        1.5,
        24.0
    );

    // Output to fragment.
    v_age_norm = clamp(age / LIFETIME, 0.0, 1.0);
    v_hue_deg = centroid_to_hue(my_centroid);
    v_intensity = (0.4 + my_rms * 0.9) * (1.0 - v_age_norm);
}
