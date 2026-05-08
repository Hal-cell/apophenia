#version 330

// PARTICLE UPDATE — transform-feedback simulation step.
//
// Reads each particle's previous state and writes the new state via
// `out` varyings (captured into a VBO by transform feedback). No
// fragment shader needed — the rasterizer is disabled by the host
// when this program runs.
//
// Per-particle state is packed into two vec4s:
//   pos_age = (pos.xyz, age)
//   vel_seed = (vel.xyz, seed)  — seed is a deterministic per-particle
//                                  random ∈ [0, 1) used to assign a
//                                  channel and randomize trajectories
//
// Update logic per frame:
//   age += dt
//   if age > LIFETIME and channel is "active" (RMS / onset above floor):
//     respawn at the channel's emitter position with audio-modulated
//     initial velocity
//   else if age > LIFETIME (channel silent):
//     park the particle far away ("dead pool") so it's not visible
//   else:
//     integrate position += velocity * dt
//     apply drag, slight gravity, swirl force (velocity rotated around
//     the world Y-axis a little — gives orbital flow)
//
// The simulation is fully deterministic given (initial state, audio
// uniforms, dt, time). Replay-friendly for video capture / debugging.

uniform float u_dt;
uniform float u_time;
uniform float u_density;        // emission strength (state.motion.density)
uniform float u_speed_scale;    // velocity multiplier (state.motion.speed)
uniform float u_onset_gain;     // onset envelope multiplier
uniform float u_rms[14];
uniform float u_onset[14];
uniform float u_centroid[14];
uniform float u_channel_weight[14];

const int N_CHANNELS = 14;
const float LIFETIME = 4.0;       // seconds; particles cycle through this
const float ACTIVITY_FLOOR = 0.02; // below this RMS+onset, channel is silent
const vec3  DEAD_POOL = vec3(0.0, -100.0, 0.0);

in vec4 in_pos_age;
in vec4 in_vel_seed;

out vec4 v_pos_age;
out vec4 v_vel_seed;

// Hash → uniform [0, 1)
float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

vec3 hash33(float p) {
    return vec3(hash11(p), hash11(p + 17.3), hash11(p + 31.7));
}

// Channel emitter ring: 14 anchors evenly spaced in XZ plane,
// slight Y wobble for variation.
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

    // Channel assignment is locked at init (via seed → integer mapping)
    // so a given particle always belongs to the same channel.
    int my_channel = int(seed * float(N_CHANNELS));
    my_channel = clamp(my_channel, 0, N_CHANNELS - 1);

    float my_rms = u_rms[my_channel];
    float my_onset = u_onset[my_channel] * u_onset_gain;
    float my_weight = u_channel_weight[my_channel];
    float activity = (my_rms + my_onset * 0.6) * my_weight;

    age += u_dt;

    if (age > LIFETIME) {
        // Channel silent → park in dead pool, don't respawn.
        if (activity < ACTIVITY_FLOOR) {
            pos = DEAD_POOL;
            vel = vec3(0.0);
            age = LIFETIME;  // stay dead, don't accumulate further
        } else {
            // Respawn at this channel's emitter. Density gates the
            // probability of respawn — sparser scenes leave some
            // particles in the dead pool.
            float gate = hash11(seed * 1373.7 + u_time * 13.0);
            if (gate > 0.15 + u_density * 0.85) {
                pos = DEAD_POOL;
                vel = vec3(0.0);
                age = LIFETIME;
            } else {
                pos = emitter_pos(my_channel);
                // Initial direction: outward + slightly random.
                vec3 out_dir = normalize(pos);  // away from origin
                vec3 jitter = (hash33(seed * 941.3 + u_time) - 0.5) * 0.6;
                vec3 dir = normalize(out_dir + jitter);
                // Initial speed scales with audio energy.
                float speed = (0.6 + my_rms * 1.5 + my_onset * 2.0)
                              * u_speed_scale;
                vel = dir * speed;
                age = 0.0;
            }
        }
    } else {
        // Live integration.
        pos += vel * u_dt;
        // Drag — slight per-frame velocity decay so particles ease in.
        vel *= 0.985;
        // Gentle gravity downward so the swarm has a settling feel.
        vel.y -= 0.4 * u_dt;
        // Swirl force: rotate velocity around world Y axis a little.
        // Strength scales with onset so transients twist the flow.
        float swirl = 0.15 * u_dt * (1.0 + my_onset * 1.5);
        float c = cos(swirl), s = sin(swirl);
        vec3 v_swirled = vec3(
            c * vel.x + s * vel.z,
            vel.y,
            -s * vel.x + c * vel.z
        );
        vel = v_swirled;
    }

    v_pos_age = vec4(pos, age);
    v_vel_seed = vec4(vel, seed);
    // gl_Position never used — no rasterizer pass — but GLSL still
    // needs a write.
    gl_Position = vec4(0.0);
}
