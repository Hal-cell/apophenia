#version 330

// Shared vertex shader for all fragment-only layer presets.
// Just passes a screen-aligned quad through; all the visual work
// happens in the fragment shaders.

in vec2 in_pos;
out vec2 v_uv;

void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
