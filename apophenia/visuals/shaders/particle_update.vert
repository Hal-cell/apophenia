#version 330

// PARTICLE UPDATE — transform-feedback simulation step.
//
// Phase-18 reshape (fluid dynamics): the per-frame jitter / drift /
// collapse problems came from a few force-model issues that I'm
// replacing here:
//
//   * smoothstep deadband on home cohesion left close particles with
//     near-zero pull, so secondary forces (noise, multi-emitter) won
//     and particles drifted away over time → REPLACED with a tanh
//     saturation that keeps strong pull even at small distances
//   * over-aggressive onset kicks (~3× speed_scale) caused whip-crack
//     jitter → SOFTENED to ~1× and ramp via envelope
//   * curl noise scale was too tight (0.45) so neighbour particles
//     saw uncorrelated forces → flow looked grainy → LOWERED to 0.28
//     so neighbours flow together (laminar)
//   * world bound at r=8 was too lax → particles drifted far → TIGHTENED
//     to r=4 with a hard-reset escape valve at r=5 (snap back to home)
//   * secondary multi-emitter pull constant 0.25 was too strong → with
//     all channels active particles got dragged to centroid →
//     REDUCED to 0.08
//
// Drag is now driven by a `u_viscosity` uniform: `vel *= mix(0.99,
// 0.92, viscosity)`. High viscosity gives thick fluid; low gives
// gaseous, lively motion.

uniform float u_dt;
uniform float u_time;
uniform float u_density;
uniform float u_speed_scale;
uniform float u_onset_gain;

uniform float u_force_noise;
uniform float u_force_vortex;
uniform float u_force_cohesion;
uniform float u_max_speed;
uniform float u_viscosity;

uniform float u_audio_intensity;
uniform float u_audio_norm;
uniform float u_rms[14];
uniform float u_onset[14];
uniform float u_centroid[14];
uniform float u_channel_weight[14];

const int N_CHANNELS = 14;
const float HOME_BIAS = 1.2;
const float ONSET_THRESHOLD = 0.3;
// Phase-18: tighter scene radius. Particles near r=4 feel a soft
// pullback; particles past r=5 get hard-reset to home.
const float SOFT_BOUND = 4.0;
const float HARD_BOUND = 5.0;

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

// Phase-18: lowered spatial frequency `s = 0.28` (was 0.45) so
// neighbour particles see correlated forces — flow looks laminar
// instead of grainy.
vec3 flow_field(vec3 p, float t) {
    float s = 0.28;
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

vec3 channel_kick_dir(int channel) {
    float i = float(channel);
    float n = float(N_CHANNELS);
    float y = 1.0 - 2.0 * (i + 0.5) / n;
    float r = sqrt(max(1.0 - y * y, 0.0));
    float az = i * 2.39996323;
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

    age += u_dt;
    if (my_onset > ONSET_THRESHOLD) {
        age = 0.0;
    }

    // Position update (semi-implicit Euler).
    pos += vel * u_dt;

    // -------- Spring-force home cohesion -------- //
    // Phase-18: replaced smoothstep deadband with `tanh(dist × 0.7)`
    // saturation. Particles within ~1 unit of home feel substantial
    // pull (was: near-zero), so home identity holds even when other
    // channels are active. tanh saturates at 1 for far particles so
    // the pull doesn't grow unbounded.
    vec3 home_em = emitter_pos(my_channel);
    vec3 to_home = home_em - pos;
    float home_dist = length(to_home);
    float home_dist_safe = max(home_dist, 1e-3);

    float home_strength = HOME_BIAS
                        + u_rms[my_channel] * u_channel_weight[my_channel] * 0.6;
    // tanh saturation gives strong pull even at close range.
    float home_pull = home_strength * tanh(home_dist * 0.7);
    vec3 cohesion_sum = (to_home / home_dist_safe) * home_pull;

    // Home vortex (audio-modulated tangential rotation around emitter).
    vec3 home_rel = pos - home_em;
    vec3 home_tan = cross(vec3(0.0, 1.0, 0.0), home_rel);
    vec3 vortex_sum = home_tan
                    * (1.0 + my_onset * 2.5)
                    / (0.6 + home_dist);

    // -------- Other channels' weak influence -------- //
    // Phase-18: secondary pull constant lowered 0.25 → 0.08 so dense
    // audio doesn't pull every particle to the centroid.
    for (int i = 0; i < N_CHANNELS; i++) {
        if (i == my_channel) continue;
        float activity_i = (u_rms[i] + u_onset[i] * 1.5)
                         * u_channel_weight[i];
        if (activity_i < 0.05) continue;

        vec3 ep    = emitter_pos(i);
        vec3 to_em = ep - pos;
        float dist = length(to_em);
        float dist_safe = max(dist, 0.4);

        float pull = activity_i
                   * smoothstep(0.5, 5.0, dist)
                   / dist_safe
                   * 0.08;
        cohesion_sum += to_em * pull;

        vec3 rel = pos - ep;
        vec3 tan_v = cross(vec3(0.0, 1.0, 0.0), rel);
        float vstr = activity_i / (0.6 + dist) * 0.18;
        vortex_sum += tan_v * vstr;
    }

    // -------- Curl-noise field -------- //
    float noise_str = u_force_noise
                    * (0.6 + u_audio_intensity * 1.4 + u_audio_norm * 0.3);
    vec3 noise_force = flow_field(pos, u_time) * noise_str;

    // -------- Apply forces -------- //
    vel += (cohesion_sum * u_force_cohesion * 1.4
          + vortex_sum   * u_force_vortex
          + noise_force) * u_dt;

    // -------- Onset directional kick (phase-17, softened by phase-18) -- //
    // Phase-18: kick magnitude lowered 3.0 → 1.0. The onset envelope
    // already decays geometrically over ~5 frames so the cumulative
    // impulse is still meaningful, just spread over time → fluid feel
    // instead of whip-crack jolt.
    if (my_onset > ONSET_THRESHOLD) {
        vec3 base_dir = channel_kick_dir(my_channel);
        vec3 jitter = (hash33(seed * 31.7 + u_time * 11.0) - 0.5) * 0.5;
        vec3 kick = normalize(base_dir + jitter);
        vel += kick * my_onset * u_speed_scale * 1.0 * u_dt;
    }

    // -------- Drag (viscosity-driven) -------- //
    // Phase-18: drag now driven by `u_viscosity`. mix(0.99, 0.92, ν).
    // High ν = sticky / oily; low = airy. The 0.92 floor still has
    // enough damping to keep simulation stable.
    float drag = mix(0.99, 0.92, u_viscosity);
    vel *= drag;

    // -------- Speed cap -------- //
    float speed = length(vel);
    if (speed > u_max_speed) {
        vel *= u_max_speed / speed;
    }

    // -------- Soft world bound -------- //
    // Particles past SOFT_BOUND feel a quadratic restoring force back
    // toward origin. Smooth — doesn't visibly clamp or kink.
    float r = length(pos);
    if (r > SOFT_BOUND) {
        float over = r - SOFT_BOUND;
        vel -= (pos / max(r, 0.01)) * over * over * 1.8 * u_dt;
    }

    // -------- Hard reset for runaways -------- //
    // Phase-18: if a particle escapes the scene (r > HARD_BOUND) or
    // its velocity exceeds 1.5× the cap (typical of accumulated kicks),
    // teleport it back to a small sphere around its home with a damped
    // velocity. Keeps the visible scene populated.
    if (r > HARD_BOUND || speed > u_max_speed * 1.5) {
        vec3 reset_jitter = (hash33(seed * 53.7 + u_time * 7.0) - 0.5) * 0.6;
        pos = home_em + reset_jitter;
        vel *= 0.3;
    }

    // Density modulates max speed implicitly (phase-14 retain).
    if (u_density < 0.5) {
        vel *= mix(0.92, 1.0, u_density * 2.0);
    }

    v_pos_age = vec4(pos, age);
    v_vel_seed = vec4(vel, seed);
    gl_Position = vec4(0.0);
}
