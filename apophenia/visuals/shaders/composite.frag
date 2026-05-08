#version 330

// COMPOSITOR — final stage that blends the shader-engine output with the
// SDXL-Turbo AI texture. Phase 6 introduces the AI side; phase 7 will
// add proper post-FX (glitch, chromatic aberration, kaleidoscope).
//
// Inputs:
//   u_shader_tex   - the offscreen FBO that ShaderEngine drew into
//   u_ai_tex       - the latest AI frame (uploaded from CPU each tick)
//   u_blend        - state.blend.shader_ai ∈ [0,1]; 0 = shader only,
//                    1 = AI only
//   u_saturation   - state.palette.saturation; 1.0 = neutral
//   u_has_ai       - 0/1 flag; when AI hasn't generated its first frame
//                    yet we fall through to shader output regardless of
//                    u_blend, so the screen isn't black on startup
//
// Output: writes to the default framebuffer.

uniform sampler2D u_shader_tex;
uniform sampler2D u_ai_tex;
uniform float     u_blend;
uniform float     u_saturation;
uniform float     u_has_ai;

in  vec2 v_uv;
out vec4 fragColor;

vec3 apply_saturation(vec3 rgb, float s) {
    // Standard luma-based desat / supersat. s=1 leaves rgb unchanged;
    // s=0 collapses to grey; s>1 over-saturates.
    float luma = dot(rgb, vec3(0.299, 0.587, 0.114));
    return mix(vec3(luma), rgb, s);
}

void main() {
    vec3 shader_rgb = texture(u_shader_tex, v_uv).rgb;
    vec3 ai_rgb     = texture(u_ai_tex,     v_uv).rgb;

    // Effective blend collapses to 0 when no AI frame has arrived yet so
    // the user sees the shader feed (instead of a black "AI" texture)
    // during SDXL warmup.
    float t = u_blend * u_has_ai;
    vec3 mixed = mix(shader_rgb, ai_rgb, t);

    mixed = apply_saturation(mixed, u_saturation);

    fragColor = vec4(mixed, 1.0);
}
