#version 330

// PARTICLE UPDATE — transform-feedback simulation step.
//
// Phase-15 redesign:
//   * Particles are PERSISTENT. No LIFETIME, no respawn, no dead
//     pool. Every particle is always alive and on screen. This kills
//     the "popping in/out" behaviour from earlier phases.
//   * Forces sum over ALL 14 emitters per particle, not just the
//     particle's home channel. Every individual particle is affected
//     by every audio channel — louder channels exert stronger pulls
//     + spin, silent ones contribute nothing. The home channel still
//     exerts a baseline pull (`HOME_BIAS`) so particles don't
//     wander forever when all channels go quiet.
//   * Onset transients now KICK velocity outward instead of
//     respawning particles. The onset envelope decays over ~30ms so
//     the kick lasts a few frames and then forces resume normal,
//     producing the classic transient-burst feel without any spawn
//     / despawn.
//   * `age` field is retained in the state layout (for ABI stability
//     with the existing 8-float packing) but is now just "time since
//     last onset kick on this particle's home channel" — used in
//     render for transient-flash brightness modulation.
//
// State packing unchanged:
//   pos_age = (pos.xyz, age)
//   vel_seed = (vel.xyz, seed)

uniform float u_dt;
uniform float u_time;
uniform float u_density;          // emission strength (state.motion.density)
uniform float u_speed_scale;      // velocity multiplier (state.motion.speed)
uniform float u_onset_gain;       // onset envelope multiplier

uniform float u_force_noise;
uniform float u_force_vortex;
uniform float u_force_cohesion;
uniform float u_max_speed;

uniform float u_audio_intensity;
uniform float u_audio_norm;
uniform float u_rms[14];
uniform float u_onset[14];
uniform float u_centroid[14];
uniform float u_channel_weight[14];

const int N_CHANNELS = 14;
const float HOME_BIAS = 1.2;       // home-channel pull (always on) — must
                                   // dominate the secondary other-channel
                                   // contributions to preserve cluster identity
const float ONSET_THRESHOLD = 0.3; // onset envelope above this triggers kick

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

// Phase-17: each channel has a unique deterministic XYZ kick
// direction. Uses golden-ratio sequencing for the azimuth + a Fibonacci
// lattice scheme for elevation — known to give very evenly-spaced
// points on a unit sphere with low pairwise alignment. Critical for
// the "every channel moves the cluster a different way" feel.
vec3 channel_kick_dir(int channel) {
    float i = float(channel);
    // Fibonacci sphere lattice (Saff & Kuijlaars):
    //   y = 1 - 2(i + 0.5)/N      — uniformly spaced cosine of latitude
    //   az = 2π × i × (1/φ²)      — golden-ratio azimuth winds
    float n = float(N_CHANNELS);
    float y = 1.0 - 2.0 * (i + 0.5) / n;
    float r = sqrt(max(1.0 - y * y, 0.0));
    float az = i * 2.39996323;  // 2π × (1 - 1/φ²) ≈ 2.39996
    return vec3(r * cos(az), y, r * sin(az));
}

void main() {
    vec3 pos = in_pos_age.xyz;
    float age = in_pos_age.w;
    vec3 vel = in_vel_seed.xyz;
    float seed = in_vel_seed.w;

    int my_channel = int(seed * float(N_CHANNELS));
    my_channel = clamp(my_channel, 0, N_CHANNELS - 1);
    float my_onset = u_onset[my_channel] * u_onset_gain;

    // age = time since last hot onset on home channel; just a counter
    // for the render shader's transient-flash modulation.
    age += u_dt;
    if (my_onset > ONSET_THRESHOLD) {
        age = 0.0;
    }

    // -------- Position update (semi-implicit Euler) -------- //
    pos += vel * u_dt;

    // -------- Forces -------- //
    // Home emitter dominates: every particle has a strong, always-on
    // pull + vortex toward its home channel's anchor (silent or not),
    // which is what gives the visual its 14-cluster identity. Each of
    // the OTHER 13 channels then contributes a small directional bias
    // only when audibly active — that's the "every particle feels
    // every channel" behaviour the user asked for, but tuned so a
    // single loud channel pulls particles slightly toward it without
    // dissolving the cluster structure entirely.

    vec3 home_em   = emitter_pos(my_channel);
    vec3 to_home   = home_em - pos;
    float home_dist = length(to_home);
    float home_dist_safe = max(home_dist, 0.4);

    // Home cohesion: smoothstep so a particle right at the emitter
    // isn't yanked. HOME_BIAS scales with home channel's activity so
    // a loud home tightens the cluster.
    float home_strength = HOME_BIAS
                        + u_rms[my_channel] * u_channel_weight[my_channel] * 0.6;
    vec3 cohesion_sum = (to_home / home_dist_safe)
                      * home_strength
                      * smoothstep(0.4, 4.0, home_dist);

    // Home vortex: always-on rotation around the home anchor; onset
    // spikes the spin.
    vec3 home_rel = pos - home_em;
    vec3 home_tan = cross(vec3(0.0, 1.0, 0.0), home_rel);
    vec3 vortex_sum = home_tan
                    * (1.0 + my_onset * 2.5)
                    / (0.6 + home_dist);

    // -------- Other channels' weak influence -------- //
    // Each other-channel contributes a weak directional pull + a
    // weak vortex bias when audibly active. Floor gates silent
    // channels so they don't add noise. Constants are deliberately
    // small (~0.25) so the home cluster survives even when many
    // other channels go loud.
    for (int i = 0; i < N_CHANNELS; i++) {
        if (i == my_channel) continue;
        float activity_i = (u_rms[i] + u_onset[i] * 1.5)
                         * u_channel_weight[i];
        if (activity_i < 0.05) continue;

        vec3 ep    = emitter_pos(i);
        vec3 to_em = ep - pos;
        float dist = length(to_em);
        float dist_safe = max(dist, 0.4);

        // Weak attractive pull, scaled by audio activity. Distance
        // falloff reaches max at dist=5 so close-by emitters pull
        // more than far-side-of-the-ring ones.
        float pull = activity_i
                   * smoothstep(0.5, 5.0, dist)
                   / dist_safe
                   * 0.25;
        cohesion_sum += to_em * pull;

        // Weak vortex contribution around this emitter.
        vec3 rel = pos - ep;
        vec3 tan = cross(vec3(0.0, 1.0, 0.0), rel);
        float vstr = activity_i / (0.6 + dist) * 0.3;
        vortex_sum += tan * vstr;
    }

    // -------- Curl-noise field -------- //
    float noise_str = u_force_noise
                    * (0.6 + u_audio_intensity * 1.4 + u_audio_norm * 0.3);
    vec3 noise_force = flow_field(pos, u_time) * noise_str;

    // -------- Apply forces -------- //
    vel += (cohesion_sum * u_force_cohesion * 1.4
          + vortex_sum   * u_force_vortex
          + noise_force) * u_dt;

    // -------- Phase-17 directional onset kick on home channel -------- //
    // Each channel has a unique XYZ direction (channel_kick_dir). On
    // a hot onset, particles in that channel get a velocity boost
    // along that direction — plus a small per-particle random jitter
    // so repeated hits don't go in EXACTLY the same direction
    // (avoids robotic feel; adds individual particle variation
    // within the cluster's collective surge). The kick is much
    // larger than the phase-15 radial kick (~3× speed) so transients
    // genuinely move the cluster, not just shimmer it.
    if (my_onset > ONSET_THRESHOLD) {
        vec3 base_dir = channel_kick_dir(my_channel);
        vec3 jitter = (hash33(seed * 31.7 + u_time * 11.0) - 0.5) * 0.6;
        vec3 kick = normalize(base_dir + jitter);
        vel += kick * my_onset * u_speed_scale * 3.0 * u_dt;
    }

    // -------- Drag (quadratic-ish) -------- //
    float speed = length(vel);
    float drag = 0.985 - 0.06 * smoothstep(1.0, 4.0, speed);
    vel *= drag;

    // -------- Speed cap -------- //
    speed = length(vel);
    if (speed > u_max_speed) {
        vel *= u_max_speed / speed;
    }

    // -------- Soft world bound -------- //
    // Without this, particles can wander to infinity if all channels
    // go silent and curl noise alone keeps pushing them. Pull anything
    // beyond r=8 gently back toward the origin.
    float r = length(pos);
    if (r > 8.0) {
        vel -= (pos / max(r, 0.01)) * (r - 8.0) * 0.6 * u_dt;
    }

    // u_density controls the "active fraction" — used to be a respawn
    // gate; now it modulates max speed implicitly via a small velocity
    // damping when density is low.
    if (u_density < 0.5) {
        vel *= mix(0.92, 1.0, u_density * 2.0);
    }

    v_pos_age = vec4(pos, age);
    v_vel_seed = vec4(vel, seed);
    gl_Position = vec4(0.0);
}
