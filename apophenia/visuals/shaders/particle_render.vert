#version 330

// PARTICLE RENDER (vertex stage) — velocity-aligned streak per particle.
//
// Phase-16: instead of rendering each particle as a single point sprite,
// each particle is a 2-vertex LINE from `pos - vel × streak_length` (tail)
// to `pos` (head). The instanced draw call binds 2 static vertices and
// instances the particle data N times, so each particle gets its own
// line drawn in screen space.
//
// `in_vertex_t` is the static-buffer per-vertex value: 0 at the tail,
// 1 at the head. We interpolate the world-space line position based on
// `t`, project to clip space, and pass `t` through to the fragment
// shader for the tail→head brightness gradient.
//
// Phase-15 brightness floor + transient flash on home-channel onset is
// retained: silent particles still render dimly (no flicker off);
// recent onsets get a brief halo.

uniform mat4  u_mvp;
uniform float u_resolution_y;
uniform float u_streak_length;   // state.force.streak_length (seconds)
uniform float u_centroid[14];
uniform float u_rms[14];

const int   N_CHANNELS = 14;
const float HUE_LO = 30.0;
const float HUE_HI = 200.0;
const float CENTROID_LO = 50.0;
const float CENTROID_HI = 12000.0;
const float FLASH_DECAY_S = 0.6;

in float in_vertex_t;            // 0 = tail, 1 = head (from line VBO)
in vec4  in_pos_age;             // per-instance: particle pos + age
in vec4  in_vel_seed;            // per-instance: particle vel + seed

out float v_t;                   // [0, 1] tail→head, for fragment gradient
out float v_flash;
out float v_hue_deg;
out float v_intensity;
out float v_speed;

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

    // ---- Streak geometry ---- //
    // Tail at pos - vel * streak_length; head at pos. Interpolate
    // via in_vertex_t (0 = tail, 1 = head).
    //
    // Floor the effective streak at a small minimum so a degenerate
    // (zero-length) line never gets culled by the rasterizer — that
    // would make particles invisible when the user dials streak to
    // 0 or when a particle is momentarily stationary. The minimum
    // (~3ms of motion) gives a 1-pixel-ish footprint at typical
    // velocities, matching the old "dot" feel.
    float effective = max(u_streak_length, 0.003);
    vec3 line_pos = pos - vel * effective * (1.0 - in_vertex_t);
    gl_Position = u_mvp * vec4(line_pos, 1.0);

    // Outputs.
    float speed = length(vel);
    float flash = exp(-age / FLASH_DECAY_S);

    v_t          = in_vertex_t;
    v_flash      = flash;
    v_hue_deg    = centroid_to_hue(my_centroid);
    // Brightness floor 0.25 keeps silent particles visible; flash adds
    // brief brightness post-onset.
    v_intensity  = 0.25 + my_rms * 0.7 + flash * 0.4;
    v_speed      = speed;
}
