#version 330

// GYROID — animated 2D slice of a 3D triply-periodic minimal surface.
//
// Maths: the gyroid is a Schoen-class TPMS defined by the implicit
// equation
//   f(x, y, z) = sin(x)·cos(y) + sin(y)·cos(z) + sin(z)·cos(x) = c
// where the constant c selects which member of a continuous family
// of surfaces we render. c=0 is the canonical area-minimising
// surface; |c| > 0 gives "thickened" sheets that don't quite touch.
//
// We rasterise the 2D slice z = u_time · drift, so the picture
// breathes through the family as time advances. The level set is
// rendered as a soft Gaussian peak around `f = c`, giving the shell
// of the surface (not the volume).
//
// Lighting: instead of a flat colour we compute the spatial gradient
// ∇f via analytic partial derivatives (no finite-diff noise) and
// shade with Lambert against a fixed light direction. This gives
// the lit-3D-form feel without actually raymarching — much cheaper
// (~30 ALU/pixel including the trig).
//
// Audio coupling:
//   * RMS shifts the level-set offset c, so loud audio "thickens"
//     the surface and reveals different topology.
//   * Centroid drives lattice scale (bassy = wide cells, bright =
//     fine grain).
//   * Onset adds a phase kick, making the topology breathe.
//
// Each channel renders the same gyroid scene from a different camera
// position (per-channel offset shift). Stacked additively across
// active channels you get a multi-perspective sense of depth.

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_rms;
uniform float u_centroid;
uniform float u_onset;
uniform float u_hue;
uniform float u_channel_weight;
uniform float u_channel;

in  vec2 v_uv;
out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// f(x, y, z) — the gyroid implicit function.
float gyroid(vec3 p) {
    return sin(p.x) * cos(p.y) + sin(p.y) * cos(p.z) + sin(p.z) * cos(p.x);
}

// Analytic gradient ∇f. Saves a finite-difference quartet of gyroid()
// calls per pixel and gives a clean, noise-free normal direction.
//   ∂f/∂x =  cos(x)cos(y) − sin(z)sin(x)
//   ∂f/∂y = −sin(x)sin(y) + cos(y)cos(z)
//   ∂f/∂z = −sin(y)sin(z) + cos(z)cos(x)
vec3 gyroid_grad(vec3 p) {
    return vec3(
         cos(p.x) * cos(p.y) - sin(p.z) * sin(p.x),
        -sin(p.x) * sin(p.y) + cos(p.y) * cos(p.z),
        -sin(p.y) * sin(p.z) + cos(p.z) * cos(p.x)
    );
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;

    // Per-channel "camera" offset — each layer renders the same TPMS
    // from a slightly shifted XY origin. Stacking additively gives
    // an implicit sense of depth-from-parallax.
    vec3 cam_offset = vec3(
        sin(u_channel * 0.97) * 1.7,
        cos(u_channel * 1.41) * 1.2,
        u_channel * 0.4
    );

    // Lattice scale: bassy = coarse, bright = fine. World-space
    // unit per screen-half is `scale`, so larger = denser geometry.
    float scale = 2.0 + clamp(u_centroid, 0.0, 12000.0) / 1500.0;

    // World-space probe point. z drifts on time + onset for a
    // breathing topology.
    vec3 p = vec3(uv * scale, u_time * 0.4 + u_onset * 1.5) + cam_offset;

    float f = gyroid(p);

    // Level-set offset c: ±0.6 from RMS. At c=0 we get the classical
    // minimal surface; |c| ≠ 0 reveals separated sheets.
    float c = (u_rms - 0.5) * 0.6;

    // Shell rendering: Gaussian peak around f = c. Width controls
    // shell thickness; tighter = sharper edges.
    float shell = exp(-(f - c) * (f - c) * 7.0);

    // Lambertian shading against a fixed light from upper-right-front.
    vec3 normal = normalize(gyroid_grad(p));
    vec3 light = normalize(vec3(0.5, 0.8, 0.4));
    float lambert = max(0.0, dot(normal, light));
    // Half-Lambert (Valve's trick): wraps the falloff past the
    // terminator so the shadow side isn't pure black, giving a
    // softer, more "luminous" read.
    float shading = 0.4 + 0.6 * (lambert * 0.5 + 0.5);

    // Falloff so each layer self-attenuates at its edges.
    float r = length(uv);
    float falloff = exp(-r * r * 0.6);

    float intensity = shell * shading * u_rms * u_channel_weight * falloff * 1.6;
    vec3 color = hsv2rgb(vec3(u_hue / 360.0, 0.7, 1.0)) * intensity;
    fragColor = vec4(color, intensity * 0.7);
}
