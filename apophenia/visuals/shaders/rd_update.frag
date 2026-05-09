#version 330

// Gray-Scott reaction-diffusion update step.
//
// Reads (U, V) from the previous-state texture (RG channels of an
// RGBA16F sim texture) and writes the next state to the FBO. Run in
// ping-pong by `apophenia.visuals.reaction_diffusion.ReactionDiffusion`.
//
// PDE:
//   ∂U/∂t = D_U · ∇²U − U·V² + F · (1 − U)
//   ∂V/∂t = D_V · ∇²V + U·V² − (F + k) · V
//
// Numerical scheme:
//   * Forward Euler in time with dt ≤ 1.0 (stable for the 5-point
//     Laplacian at unit spacing).
//   * 5-point Laplacian: L(u) = u(x-1) + u(x+1) + u(y-1) + u(y+1) − 4u(x).
//   * Boundary: clamped (CLAMP_TO_EDGE on the texture) so edges
//     replicate themselves, avoiding garbage at the borders.
//
// At the trivial fixed point (U=1, V=0) the system stays homogeneous
// forever. The simulator seeds a small disc of V≈0.5 at init time so
// the pattern has something to grow from.

uniform sampler2D u_sim;
uniform vec2  u_size;     // grid dimensions in texels
uniform float u_F;        // feed rate
uniform float u_k;        // kill rate
uniform float u_DU;       // diffusion of U
uniform float u_DV;       // diffusion of V
uniform float u_dt;       // timestep (≤ 1.0)

in  vec2 v_uv;
out vec4 fragColor;

void main() {
    // Texel size in UV space.
    vec2 texel = 1.0 / u_size;

    // Centre + 4 neighbours.
    vec2 c  = texture(u_sim, v_uv).rg;
    vec2 l  = texture(u_sim, v_uv - vec2(texel.x, 0.0)).rg;
    vec2 r  = texture(u_sim, v_uv + vec2(texel.x, 0.0)).rg;
    vec2 d  = texture(u_sim, v_uv - vec2(0.0, texel.y)).rg;
    vec2 t  = texture(u_sim, v_uv + vec2(0.0, texel.y)).rg;

    // 5-point Laplacian. (u, v) component-wise.
    vec2 lap = (l + r + d + t) - 4.0 * c;

    // Reaction term.
    float u = c.x;
    float v = c.y;
    float reaction = u * v * v;

    // PDE step.
    float du = u_DU * lap.x - reaction + u_F * (1.0 - u);
    float dv = u_DV * lap.y + reaction - (u_F + u_k) * v;

    float new_u = u + u_dt * du;
    float new_v = v + u_dt * dv;

    // Clamp to [0, 1] — Gray-Scott values can transiently overshoot
    // due to the linear PDE step before the nonlinear reaction
    // re-pulls them; clamping prevents the texture from accumulating
    // out-of-bound junk that would propagate via the Laplacian.
    new_u = clamp(new_u, 0.0, 1.0);
    new_v = clamp(new_v, 0.0, 1.0);

    fragColor = vec4(new_u, new_v, 0.0, 1.0);
}
