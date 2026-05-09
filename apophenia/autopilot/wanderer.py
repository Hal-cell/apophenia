"""1D smooth-noise generator for autopilot parameter trajectories.

Each `Wanderer` produces a continuous, deterministic `f(t) ∈ [-1, 1]`
driven by 4-octave 1D value noise. Sampling is stateless — same `(t,
seed)` always gives the same value — so wanderers are reproducible and
trivially thread-safe.

Use different `seed` values for parameters whose trajectories should
be uncorrelated. Use different `period_s` for parameters whose
trajectories should evolve at different timescales.

Maths:
  * `_hash11(p, seed)` — sin-based hash → float in [-1, 1].
    Cheap, smooth-ish, good enough for visual modulation.
  * `_value_noise_1d(x, seed)` — bilinearly-interpolated hashes at
    integer grid points, smoothed with `s = 3f² - 2f³` (the
    Hermite smoothstep) for C¹ continuity.
  * `Wanderer.value(t)` — sums 4 octaves at frequencies 1, 2, 4, 8
    over the base period, with amplitude halving each octave.
    Result is normalised back to [-1, 1].
"""

from __future__ import annotations

import math


def _hash11(p: float, seed: int) -> float:
    """Deterministic float-to-float hash returning a value in [-1, 1].
    Smooth enough to look "natural" when sampled at adjacent inputs;
    not cryptographic.
    """
    h = math.sin(p * 12.9898 + seed * 78.233) * 43758.5453
    return (h - math.floor(h)) * 2.0 - 1.0


def _value_noise_1d(x: float, seed: int) -> float:
    """Smooth 1D value noise. Hash at integer grid points, smoothstep-
    interpolate the fractional part. Returns a value in [-1, 1] with
    C¹ continuity (no piecewise-linear kinks).
    """
    i = math.floor(x)
    f = x - i
    s = f * f * (3.0 - 2.0 * f)  # Hermite smoothstep
    a = _hash11(float(i), seed)
    b = _hash11(float(i + 1), seed)
    return a + s * (b - a)


class Wanderer:
    """Slowly-drifting deterministic value `f(t) ∈ [-1, 1]`.

    Multi-octave value noise: 4 octaves at frequencies 2⁰..2³ over the
    base period, amplitudes halving each octave. Reads as organic
    rather than mechanical — short-term wobbles ride on long-term
    drift, like a temperature curve or a slow tidal flow.
    """

    OCTAVES = 4

    def __init__(self, seed: int, period_s: float = 30.0) -> None:
        if period_s <= 0:
            raise ValueError("period_s must be > 0")
        self.seed = seed
        self.period_s = period_s

    def value(self, t: float) -> float:
        """Sample at wallclock seconds `t`. Always in [-1, 1]."""
        v = 0.0
        amp = 1.0
        total = 0.0
        for i in range(self.OCTAVES):
            x = (t / self.period_s) * (1 << i)
            # Each octave gets a distinct hash seed offset so the same
            # underlying noise function isn't re-used at different
            # scales (which would correlate octaves).
            v += amp * _value_noise_1d(x, self.seed + i * 1009)
            total += amp
            amp *= 0.5
        return v / total
