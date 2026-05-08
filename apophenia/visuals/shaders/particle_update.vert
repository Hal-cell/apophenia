#version 330

// PARTICLE UPDATE — transform-feedback simulation step.
//
// Phase-13 changes:
//   * Replaced the cheap Y-axis swirl with a 3D flow-field force —
//     three offset noise samples form a smoothly-varying vector field.
//     Particles bend along curves instead of streaming radially.
//   * Onset weighting in the respawn formula is now multiplicative
//     (~6× over RMS) so transients dominate; a sharp hit produces a
//     visible explosive burst at the channel's emitter, distinct from
//     the slow drip of RMS-only flow.
//   * `u_audio_intensity` (sum of RMS, normalised) modulates flow-field
//     magnitude — louder mixes = harder turbulence.
//   * `u_audio_norm` is the CLAP embedding norm, also scales the
//     field; gives slow timbre changes a long-arc effect on motion.
//
// Per-particle state stays packed as:
//   pos_age = (pos.xyz, age)
//   vel_seed = (vel.xyz, seed)

uniform float u_dt;
uniform float u_time;
uniform float u_density;        // emission strength (state.motion.density)
uniform float u_speed_scale;    // velocity multiplier (state.motion.speed)
uniform float u_onset_gain;     // onset envelope multiplier
uniform float u_audio_intensity; // ∑ rms / 14, clamped — drives flow strength
uniform float u_audio_norm;     // CLAP embedding norm (or 0 if --no-clap)
uniform float u_rms[14];
uniform float u_onset[14];
uniform float u_centroid[14];
uniform float u_channel_weight[14];

const int N_CHANNELS = 14;
const float LIFETIME = 4.0;        // seconds; particles cycle on this period
const float ACTIVITY_FLOOR = 0.02; // below this RMS+onset, channel is silent
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

// 3D value noise: 8-corner trilinear interp of hashed lattice values.
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

// Cheap pseudo-curl flow field — three offset noise samples form a
// smoothly varying 3D vector field. Not strictly divergence-free
// (real curl noise needs ~18 samples for the gradient of a vector
// potential), but visually does the same job: particles follow
// organic flow lines instead of straight radial drift.
vec3 flow_field(vec3 p, float t) {
    float s = 0.45;  // spatial scale — coarser noise = larger eddies
    float ts = 0.18; // temporal scale — slower → gentler weather
    return vec3(
        vnoise3(p * s + vec3(t * ts,  0.0,         0.0))  - 0.5,
        vnoise3(p * s + vec3(13.0,    17.0,        t * ts * 1.3)) - 0.5,
        vnoise3(p * s + vec3(7.0,     23.0 + t*ts, 31.0)) - 0.5
    ) * 2.0; // remap [0, 1] → [-1, 1]
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

    // Onset-dominant activity: a transient hit (onset_envelope ≈ 1.0)
    // contributes ~6× more to activity than steady RMS, so percussive
    // events spawn visibly explosive bursts.
    float activity = (my_rms + my_onset * 5.0) * my_weight;

    age += u_dt;

    if (age > LIFETIME) {
        if (activity < ACTIVITY_FLOOR) {
            pos = DEAD_POOL;
            vel = vec3(0.0);
            age = LIFETIME;
        } else {
            // Density gates respawn probability. Onset events also push
            // the gate threshold up — guarantees a fast spawn rate
            // immediately after a transient.
            float gate = hash11(seed * 1373.7 + u_time * 13.0);
            float gate_thresh = 0.15 + u_density * 0.85
                              + my_onset * 0.4;  // boost on hits
            if (gate > gate_thresh) {
                pos = DEAD_POOL;
                vel = vec3(0.0);
                age = LIFETIME;
            } else {
                pos = emitter_pos(my_channel);
                vec3 out_dir = normalize(pos);
                vec3 jitter = (hash33(seed * 941.3 + u_time) - 0.5) * 0.6;
                vec3 dir = normalize(out_dir + jitter);
                // Initial speed scales with audio energy — onsets give
                // the particle a noticeably bigger initial kick.
                float speed = (0.5 + my_rms * 1.2 + my_onset * 3.0)
                              * u_speed_scale;
                vel = dir * speed;
                age = 0.0;
            }
        }
    } else {
        // Live integration with flow-field force.
        pos += vel * u_dt;
        // Drag.
        vel *= 0.985;
        // Mild gravity.
        vel.y -= 0.4 * u_dt;
        // 3D flow-field force. Strength scales with overall mix
        // intensity + CLAP embedding norm, so loud / timbrally rich
        // mixes drive harder turbulence than steady drones.
        vec3 force = flow_field(pos, u_time);
        float strength = 0.6 + u_audio_intensity * 1.4 + u_audio_norm * 0.3;
        vel += force * strength * u_dt;
    }

    v_pos_age = vec4(pos, age);
    v_vel_seed = vec4(vel, seed);
    gl_Position = vec4(0.0);
}
