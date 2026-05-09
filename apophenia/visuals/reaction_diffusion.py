"""Gray-Scott reaction-diffusion simulator on the GPU.

The Gray-Scott model is a 2-species PDE that produces beautiful
emergent Turing patterns (spots / stripes / mazes / pulses) from a
small initial perturbation. The math:

    ∂U/∂t = D_U · ∇²U  −  UV²  +  F · (1 − U)
    ∂V/∂t = D_V · ∇²V  +  UV²  −  (F + k) · V

`U` is the "substrate" concentration (replenished by F·(1−U) — the
"feed" rate). `V` is the "activator" — it consumes U via the UV²
term, then itself decays at rate (F + k) — the "kill" rate. Different
(F, k) values land in different regions of the Pearson parameter
phase diagram, giving qualitatively different patterns:

    F=0.054, k=0.062  →  spots / mitosis (the classic; default)
    F=0.025, k=0.060  →  stripes / fingerprints
    F=0.039, k=0.058  →  worms
    F=0.014, k=0.054  →  solitons (travelling pulses)

Implementation:
  * Two ping-pong RGBA16F textures at 256² (cheap to update; sampled
    bilinearly at full screen resolution by the visual shader).
  * The 5-point Laplacian is stable at unit spacing with dt = 1.0.
  * Sub-stepped: we advance `sub_steps` PDE steps per frame so
    pattern evolution is visible at human timescales (a few minutes
    of real time = many minutes of simulated time).
  * Initial state: U=1 everywhere, V seeded with a small disc of
    V=0.5 in the centre — this is the canonical Gray-Scott
    initial perturbation that grows into the pattern over time.
"""

from __future__ import annotations

from pathlib import Path

import moderngl
import numpy as np

SHADER_DIR = Path(__file__).parent / "shaders"


class ReactionDiffusion:
    """GPU-side Gray-Scott reaction-diffusion simulation."""

    DEFAULT_SIZE = (256, 256)
    # Pearson region: spots / mitosis. The classic Gray-Scott spec.
    DEFAULT_F = 0.054
    DEFAULT_K = 0.062
    # Diffusion rates; ratio D_U / D_V ~ 2 is the standard Gray-Scott
    # value that gives Turing instability.
    DIFF_U = 0.16
    DIFF_V = 0.08

    def __init__(
        self,
        ctx: moderngl.Context,
        size: tuple[int, int] = DEFAULT_SIZE,
        F: float = DEFAULT_F,  # noqa: N803 — Gray-Scott literature convention
        k: float = DEFAULT_K,
    ) -> None:
        self.ctx = ctx
        self.size = size
        self.F = F
        self.k = k

        # ---- update program ---- #
        # The update shader uses the same shared quad.vert as the layer
        # presets — full-screen quad, no geometry magic.
        vert_src = (SHADER_DIR / "quad.vert").read_text()
        update_src = (SHADER_DIR / "rd_update.frag").read_text()
        self.update_program = ctx.program(
            vertex_shader=vert_src, fragment_shader=update_src
        )
        # Fixed sampler unit binding.
        try:
            self.update_program["u_sim"].value = 0  # type: ignore[union-attr]
        except KeyError:
            pass

        quad = np.array(
            [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad.tobytes())
        self.vao = ctx.simple_vertex_array(self.update_program, self.vbo, "in_pos")

        # ---- ping-pong simulation textures ---- #
        # RGBA16F for headroom: Gray-Scott values stay in [0, 1] but
        # intermediate Laplacian sums can exceed that, and uint8
        # quantisation (256 levels) loses too much precision in the
        # tiny per-step deltas.
        self._textures = [self._fresh_sim_texture() for _ in range(2)]
        self._fbos = [
            ctx.framebuffer(color_attachments=[t]) for t in self._textures
        ]
        self._read_idx = 0  # which texture to sample on the next step

        # Seed initial state into both textures.
        seed = self._initial_state()
        for tex in self._textures:
            tex.write(seed.tobytes())

    def _fresh_sim_texture(self) -> moderngl.Texture:
        """Allocate one RGBA16F simulation texture with linear filter
        + clamped wrap (so the Laplacian at the boundary uses repeated
        edge values, not garbage from the other side)."""
        tex = self.ctx.texture(self.size, components=4, dtype="f2")
        tex.repeat_x = False
        tex.repeat_y = False
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return tex

    def _initial_state(self) -> np.ndarray:
        """Build the cold-start (U, V, _, 1) buffer.

        Standard Gray-Scott initial condition:
          * U = 1 everywhere (substrate full).
          * V = 0 except a small disc of V ≈ 0.5 in the centre (the
            seed perturbation that the system will grow from). Without
            this seed the system stays at the trivial fixed point
            U=1, V=0 forever.
        """
        h, w = self.size[1], self.size[0]
        arr = np.zeros((h, w, 4), dtype=np.float16)
        arr[..., 0] = 1.0  # U = 1 substrate
        arr[..., 3] = 1.0  # alpha (unused but valid)

        # Small randomised seed disc — a few px patches of activator V.
        # Multiple seeds rather than one big disc so the pattern has
        # multiple growth fronts that interact, accelerating visual
        # complexity vs. a single radial spot.
        rng = np.random.default_rng(0)
        n_seeds = 8
        for _ in range(n_seeds):
            cy = int(rng.integers(h // 4, 3 * h // 4))
            cx = int(rng.integers(w // 4, 3 * w // 4))
            r = int(rng.integers(3, 8))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dy * dy + dx * dx > r * r:
                        continue
                    yy, xx = cy + dy, cx + dx
                    if 0 <= yy < h and 0 <= xx < w:
                        arr[yy, xx, 1] = 0.5  # V seed
        return arr

    @property
    def texture(self) -> moderngl.Texture:
        """The latest simulation texture — bind this in the visual shader."""
        return self._textures[self._read_idx]

    def step(
        self,
        sub_steps: int = 5,
        dt: float = 1.0,
    ) -> None:
        """Advance the simulation by `sub_steps` PDE steps.

        Each step samples the current texture, applies the Gray-Scott
        update at every pixel, and writes the next state into the
        OTHER texture; then the read/write indices flip.

        Sub-stepping multiplies pattern evolution speed without
        increasing dt (which would be unstable past ~1.0 for the
        5-point Laplacian at unit spacing).
        """
        # Save the caller's framebuffer + viewport so we can restore.
        # The simulation runs at 256², not at the window resolution.
        prev_fbo = self.ctx.fbo
        prev_viewport = self.ctx.viewport

        # Diffusion + reaction parameters are constant for the whole
        # batch of sub-steps — set them once.
        try:
            self.update_program["u_size"].value = self.size  # type: ignore[union-attr]
            self.update_program["u_F"].value = self.F  # type: ignore[union-attr]
            self.update_program["u_k"].value = self.k  # type: ignore[union-attr]
            self.update_program["u_DU"].value = self.DIFF_U  # type: ignore[union-attr]
            self.update_program["u_DV"].value = self.DIFF_V  # type: ignore[union-attr]
            self.update_program["u_dt"].value = float(dt)  # type: ignore[union-attr]
        except KeyError:
            pass  # defensive — composite shaders skip missing uniforms

        for _ in range(sub_steps):
            write_idx = 1 - self._read_idx
            self._textures[self._read_idx].use(location=0)
            self._fbos[write_idx].use()
            self.ctx.viewport = (0, 0, self.size[0], self.size[1])
            self.vao.render(moderngl.TRIANGLE_STRIP)
            self._read_idx = write_idx

        # Restore caller framebuffer + viewport.
        if prev_fbo is not None:
            prev_fbo.use()
        self.ctx.viewport = prev_viewport

    def reseed(self) -> None:
        """Reset both textures to the cold-start seed pattern.

        Useful for re-perturbing the simulation if it drifts to a
        homogeneous state (rare with the default seed but possible
        for some F/k values).
        """
        seed = self._initial_state()
        for tex in self._textures:
            tex.write(seed.tobytes())
