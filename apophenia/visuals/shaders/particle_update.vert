#version 330

// PARTICLE UPDATE — transform-feedback simulation step.
//
// Phase-14 force model (TD-cluster + Ikeda fluid look):
//
//   1. CURL-NOISE flow      — three offset 3D-value-noise samples form a
//                             smoothly varying vector field. Particles
//                             bend along organic flow lines.
//   2. VORTEX               — tangential rotation around each particle's
//                             emitter, axis = world Y. Onset boosts it
//                             so transients spin the swarm.
//   3. COHESION             — gentle pull toward the emitter. Keeps the
//                             swarm clustered instead of scattering.
//                             This is the "fluid cluster" lever.
//   4. DRAG                 — quadratic-ish: drag scales with current
//                             speed so high-velocity particles slow
//                             quickly while low-velocity ones drift.
//   5. SPEED CAP            — clamp |vel| ≤ max_speed for terminal
//                             velocity / fluid feel.
//
// Phase-13 stuff retained: onset weighting in respawn (hits spawn
// bursts even on near-silent channels); CLAP audio_norm boosts noise
// strength; audio_intensity boosts noise strength.

uniform float u_dt;
uniform float u_time;
uniform float u_density;          // emission strength (state.motion.density)
uniform float u_speed_scale;      // velocity multiplier (state.motion.speed)
uniform float u_onset_gain;       // onset envelope multiplier

// Phase-14 force strengths (state.force.*).
uniform float u_force_noise;
uniform float u_force_vortex;
uniform float u_force_cohesion;
uniform float u_max_speed;

uniform float u_audio_intensity;  // ∑ rms / 14, clamped — drives noise
uniform float u_audio_norm;       // CLAP embedding norm (or 0 if --no-clap)
uniform float u_rms[14];
uniform float u_onset[14];
uniform float u_centroid[14];
uniform float u_channel_weight[14];

const int N_CHANNELS = 14;
const float LIFETIME = 4.0;
const float ACTIVITY_FLOOR = 0.02;
const vec3  DEAD_POOL = vec3(0.0, -100.0, 0.0);

in vec4 in_pos_age;
in vec4 in_vel_seed;

out vec4 v_pos_age;
out vec4 v_vel_seed;

float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

vec3 hash33(float p) {
    return vec3(hash11(p), hash11(p + 17.3), hash11(p + 31.7));
}

float vnoise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n000 = hash11(dot(i,                     vec3(1.0, 17.7, 31.1)));
    float n100 = hash11(dot(i + vec3(1, 0, 0),     vec3(1.0, 17.7, 31.1)));
    float n010 = hash11(dot(i + vec3(0, 1, 0),     vec3(1.0, 17.7, 31.1)));
    float n110 = hash11(dot(i + vec3(1, 1, 0),     vec3(1.0, 17.7, 31.1)));
    float n001 = hash11(dot(i + vec3(0, 0, 1),     vec3(1.0, 17.7, 31.1)));
    float n101 = hash11(dot(i + vec3(1, 0, 1),     vec3(1.0, 17.7, 31.1)));
    float n011 = hash11(dot(i + vec3(0, 1, 1),     vec3(1.0, 17.7, 31.1)));
    float n111 = hash11(dot(i + vec3(1, 1, 1),     vec3(1.0, 17.7, 31.1)));
    return mix(
        mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
        mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y),
        f.z
    );
}

vec3 flow_field(vec3 p, float t) {
    float s = 0.45;
    float ts = 0.18;
    return vec3(
        vnoise3(p * s + vec3(t * ts,        0.0,         0.0))         - 0.5,
        vnoise3(p * s + vec3(13.0,          17.0,        t * ts * 1.3)) - 0.5,
        vnoise3(p * s + vec3(7.0,           23.0 + t*ts, 31.0))         - 0.5
    ) * 2.0;
}

vec3 emitter_pos(int channel) {
    float angle = float(channel) / float(N_CHANNELS) * 6.2831853;
    float radius = 1.6;
    return vec3(cos(angle) * radius,
                sin(float(channel) * 0.91) * 0.25,
                sin(angle) * radius);
}

void main() {
    vec3 pos = in_pos_age.xyz;
    float age = in_pos_age.w;
    vec3 vel = in_vel_seed.xyz;
    float seed = in_vel_seed.w;

    int my_channel = int(seed * float(N_CHANNELS));
    my_channel = clamp(my_channel, 0, N_CHANNELS - 1);

    float my_rms = u_rms[my_channel];
    float my_onset = u_onset[my_channel] * u_onset_gain;
    float my_weight = u_channel_weight[my_channel];

    // Onset-dominant activity (phase 13 retained).
    float activity = (my_rms + my_onset * 5.0) * my_weight;

    age += u_dt;

    if (age > LIFETIME) {
        if (activity < ACTIVITY_FLOOR) {
            // Channel silent → stay parked.
            pos = DEAD_POOL;
            vel = vec3(0.0);
            age = LIFETIME;
        } else {
            float gate = hash11(seed * 1373.7 + u_time * 13.0);
            float gate_thresh = 0.15 + u_density * 0.85 + my_onset * 0.4;
            if (gate > gate_thresh) {
                pos = DEAD_POOL;
                vel = vec3(0.0);
                age = LIFETIME;
            } else {
                vec3 emitter = emitter_pos(my_channel);
                // Phase-14: spawn TIGHTLY around the emitter. Smaller
                // jitter → particles cluster from birth rather than
                // fanning out. Cohesion will keep them close as they
                // age.
                vec3 spawn_jitter = (hash33(seed * 941.3 + u_time) - 0.5) * 0.25;
                pos = emitter + spawn_jitter;
                // Initial velocity: small outward kick + some randomness,
                // scaled by audio.
                vec3 out_dir = normalize(pos - vec3(0.0));
                vec3 dir_jitter = (hash33(seed * 19.7 + u_time * 3.1) - 0.5) * 1.2;
                vec3 dir = normalize(out_dir + dir_jitter);
                float speed = (0.3 + my_rms * 0.7 + my_onset * 1.4)
                              * u_speed_scale;
                vel = dir * speed;
                age = 0.0;
            }
        }
    } else {
        // Live integration with the multi-force model.
        // Position update first (semi-implicit Euler).
        pos += vel * u_dt;

        vec3 emitter = emitter_pos(my_channel);
        vec3 to_emitter = emitter - pos;
        float emitter_dist = length(to_emitter);

        // -------- 1. Curl-noise flow -------- //
        // Strength bumped by audio energy + CLAP timbre.
        float noise_str = u_force_noise
                          * (0.6 + u_audio_intensity * 1.4 + u_audio_norm * 0.3);
        vec3 noise_force = flow_field(pos, u_time) * noise_str;

        // -------- 2. Vortex around emitter -------- //
        // Tangential force in the XZ plane around the emitter. Onset
        // dramatically boosts the spin so transients = whirlpool kicks.
        // Strength tapers with distance so far-away particles aren't
        // yanked back.
        vec3 rel = pos - emitter;
        vec3 tangent = cross(vec3(0.0, 1.0, 0.0), rel);
        float vortex_falloff = 1.0 / (0.4 + emitter_dist);
        vec3 vortex_force = tangent * (
            u_force_vortex * vortex_falloff
            * (1.0 + my_onset * 2.5)
        );

        // -------- 3. Cohesion: pull toward emitter -------- //
        // Use smoothstep so particles right next to the emitter aren't
        // crushed into it (would just oscillate); only pulls particles
        // that have drifted out beyond ~0.4 units.
        float pull_str = u_force_cohesion
                       * smoothstep(0.4, 3.0, emitter_dist)
                       * my_weight;
        vec3 cohesion_force = (emitter_dist > 1e-3
            ? to_emitter / emitter_dist
            : vec3(0.0)) * pull_str * 1.2;

        // -------- Apply forces -------- //
        vel += (noise_force + vortex_force + cohesion_force) * u_dt;

        // -------- 4. Drag (quadratic-ish) -------- //
        float speed = length(vel);
        float drag = 0.985 - 0.06 * smoothstep(1.0, 4.0, speed);
        vel *= drag;

        // -------- 5. Speed cap -------- //
        speed = length(vel);
        if (speed > u_max_speed) {
            vel *= u_max_speed / speed;
        }
    }

    v_pos_age = vec4(pos, age);
    v_vel_seed = vec4(vel, seed);
    gl_Position = vec4(0.0);
}
