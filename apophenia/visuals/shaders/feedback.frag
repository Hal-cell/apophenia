#version 330

// FEEDBACK — frame-to-frame trail accumulation. Sample the current
// shader output and the previous-frame feedback FBO, max-blend them,
// and write to the new feedback FBO. The compositor's post-FX pass
// then runs over this trailed output.
//
// Max blend (rather than additive or screen) keeps bright bits as
// streaks without saturating into white — the classic modular-video
// feedback look. `u_trail` decays the previous frame; values near 1
// give long trails, values near 0 collapse to no-trail.

uniform sampler2D u_shader_tex;
uniform sampler2D u_prev_feedback;
uniform float     u_trail;

in  vec2 v_uv;
out vec4 fragColor;

void main() {
    vec3 shader = texture(u_shader_tex, v_uv).rgb;
    vec3 prev   = texture(u_prev_feedback, v_uv).rgb;
    vec3 mixed  = max(shader, prev * u_trail);
    fragColor = vec4(mixed, 1.0);
}
