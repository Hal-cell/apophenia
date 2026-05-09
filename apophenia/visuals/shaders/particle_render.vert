#version 330

// PARTICLE RENDER (vertex stage) — phase-20 billboard ribbon.
//
// Each particle now renders as a 4-vertex GL_TRIANGLE_STRIP quad
// oriented along its velocity vector but perpendicular to the view
// direction (camera-facing billboard). This replaces the phase-16
// 2-vertex GL_LINES streak — quads can be any pixel width, while
// macOS GL caps glLineWidth at 1px.
//
// Static geometry per quad: 4 (u, v) pairs:
//   (0, 0) = tail-left, (1, 0) = head-left,
//   (0, 1) = tail-right, (1, 1) = head-right
// in_vertex_uv.x = head/tail t (0 = tail, 1 = head)
// in_vertex_uv.y = side (0 = -width, 1 = +width)
//
// Per-instance attributes are the existing particle state buffer
// (pos_age + vel_seed). Camera position is passed as a uniform so
// the vertex shader can compute the view direction for billboarding.

uniform mat4  u_mvp;
uniform vec3  u_camera_pos;
uniform float u_streak_length;
uniform float u_streak_width;
uniform float u_centroid[14];
uniform float u_rms[14];

const int   N_CHANNELS = 14;
const float HUE_LO = 30.0;
const float HUE_HI = 200.0;
const float CENTROID_LO = 50.0;
const float CENTROID_HI = 12000.0;
const float FLASH_DECAY_S = 0.6;

in vec2 in_vertex_uv;            // (head_t, side) per static-quad vertex
in vec4 in_pos_age;              // per-instance
in vec4 in_vel_seed;             // per-instance

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

    // ---- Streak head/tail position ---- //
    // Tail at pos - vel × streak_length, head at pos. Floor effective
    // length so even degenerate (zero-velocity) particles get a tiny
    // visible footprint.
    float effective_len = max(u_streak_length, 0.003);
    vec3 line_pos = pos - vel * effective_len * (1.0 - in_vertex_uv.x);

    // ---- Billboard width offset ---- //
    // Right vector: perpendicular to both (velocity direction) and
    // (view direction), so the ribbon faces the camera no matter how
    // the camera orbits. If velocity is near-zero (parked particle),
    // fall back to a deterministic right direction so the ribbon
    // doesn't collapse.
    float speed = length(vel);
    vec3 vel_dir = (speed > 1e-3) ? (vel / speed) : vec3(1.0, 0.0, 0.0);
    vec3 view_dir = line_pos - u_camera_pos;
    float view_len = length(view_dir);
    if (view_len > 1e-4) view_dir /= view_len;
    vec3 right = cross(vel_dir, view_dir);
    float right_len = length(right);
    // Cross product can be near-zero when vel is parallel to view —
    // fall back to world-up cross instead.
    if (right_len < 1e-3) {
        right = cross(vel_dir, vec3(0.0, 1.0, 0.0));
        right_len = length(right);
        if (right_len > 1e-4) right /= right_len;
        else                  right = vec3(0.0, 1.0, 0.0);
    } else {
        right /= right_len;
    }

    // Side ∈ [-1, +1] from in_vertex_uv.y ∈ [0, 1].
    float side = in_vertex_uv.y * 2.0 - 1.0;
    line_pos += right * u_streak_width * side;

    gl_Position = u_mvp * vec4(line_pos, 1.0);

    // ---- Outputs to fragment ---- //
    float flash = exp(-age / FLASH_DECAY_S);

    v_t          = in_vertex_uv.x;
    v_flash      = flash;
    v_hue_deg    = centroid_to_hue(my_centroid);
    v_intensity  = 0.25 + my_rms * 0.7 + flash * 0.4;
    v_speed      = speed;
}
