#version 330

// PARTICLE RENDER (vertex stage) — projects each particle to clip
// space and computes its screen-space size + colour, which the
// fragment stage uses to draw a soft sprite.
//
// Phase-15 reshape: `age` is now "time since the home channel last
// onset-kicked this particle", not "time since spawn". Used as a
// transient-flash term — particles that just got kicked render
// brighter for a few hundred ms then settle back to the steady-state
// brightness driven by RMS + velocity. Particles never die, never
// despawn — they are always rendered.

uniform mat4  u_mvp;
uniform float u_resolution_y;
uniform float u_centroid[14];
uniform float u_rms[14];

const int   N_CHANNELS = 14;
const float HUE_LO = 30.0;
const float HUE_HI = 200.0;
const float CENTROID_LO = 50.0;
const float CENTROID_HI = 12000.0;
const float FLASH_DECAY_S = 0.6;   // age-since-onset over which the flash fades

in vec4 in_pos_age;
in vec4 in_vel_seed;

out float v_flash;        // [0, 1] transient-flash term
out float v_hue_deg;
out float v_intensity;    // base brightness
out float v_speed;        // for fragment-side velocity-glow

float centroid_to_hue(float hz) {
    if (hz <= CENTROID_LO) return HUE_LO;
    if (hz >= CENTROID_HI) return HUE_HI;
    float f = (hz - CENTROID_LO) / (CENTROID_HI - CENTROID_LO);
    return HUE_LO + f * (HUE_HI - HUE_LO);
}

void main() {
    vec3 pos  = in_pos_age.xyz;
    float age = in_pos_age.w;
    vec3 vel  = in_vel_seed.xyz;
    float seed = in_vel_seed.w;

    int my_channel = int(seed * float(N_CHANNELS));
    my_channel = clamp(my_channel, 0, N_CHANNELS - 1);
    float my_rms = u_rms[my_channel];
    float my_centroid = u_centroid[my_channel];

    gl_Position = u_mvp * vec4(pos, 1.0);

    // Sprite size: small base, scaled by RMS + flash, inversely by depth.
    float depth = max(gl_Position.w, 0.5);
    float speed = length(vel);

    // Transient flash: 1.0 right after onset, decaying exponentially.
    float flash = exp(-age / FLASH_DECAY_S);

    // World-size in units; flash makes particles visibly puff up on hits.
    float world_size = 0.025
                     * (0.5 + my_rms * 1.0 + flash * 0.8 + speed * 0.2);
    gl_PointSize = clamp(
        world_size * u_resolution_y / depth,
        1.5,
        20.0
    );

    // Outputs.
    v_flash = flash;
    v_hue_deg = centroid_to_hue(my_centroid);
    // Base intensity: always nonzero so silent particles still render
    // dimly (the user wanted them persistent, not flickering off).
    v_intensity = 0.25 + my_rms * 0.7 + flash * 0.4;
    v_speed = speed;
}
