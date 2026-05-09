"""Self-evolving VisualState generator.

Each frame the renderer calls `Modulator.state(time_s, features)`.
The modulator returns a fresh `VisualState` built from:

  1. A bank of independent `Wanderer`s, each at a different timescale
     and seeded uncorrelated, providing smooth long-term drift for
     every shader-relevant parameter.

  2. Per-frame audio features (RMS / onset envelope) layered on top:
     loud audio brightens, transient hits push glitch / chromatic /
     bloom briefly higher.

Design goals (in priority order):

  * Never repeats. The 8 wanderers' periods (120 / 60 / 45 / 40 / 35 /
    25 / 20 / 180 seconds) are pairwise coprime-ish ratios, so the
    composite trajectory has effectively infinite period.
  * Stays musical. Audio coupling is multiplicative + additive so a
    quiet section reads as quiet, a hit reads as a hit.
  * Coherent macro mood. Hue and saturation drift slowest (~1-2 min),
    so the picture has stable "color identity" for a while before
    morphing.
  * Occasional surprise. Rare events (kaleidoscope shifts, brief
    freezes, glitch storms) emerge from threshold crossings of the
    slow wanderers, so they're unpredictable but not arbitrary.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from apophenia.autopilot.wanderer import Wanderer
from apophenia.state import (
    FxState,
    PaletteState,
    TransportState,
    VisualState,
)

if TYPE_CHECKING:
    from apophenia.audio.features_fast import FastFeatures


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class Modulator:
    """Builds a `VisualState` from `(time_s, features)` deterministically.

    Pure function of inputs (modulo the `seed` argument fixing the
    wanderer trajectories). Stateless across frames; the renderer
    calls `state(...)` every frame and replaces the visual state
    wholesale — this makes the system trivially reproducible and
    keeps no hidden buffers.
    """

    def __init__(self, seed: int = 0) -> None:
        # Pairwise distinct timescales so parameters never sync up.
        # Picked roughly: hue + saturation slowest (so the picture has
        # a stable "color identity" lasting tens of seconds), bloom
        # mid-term, glitch / chromatic / kaleidoscope short-term,
        # freeze rare and slow.
        self.w_hue        = Wanderer(seed=seed + 1, period_s=120.0)
        self.w_sat        = Wanderer(seed=seed + 2, period_s=60.0)
        self.w_bloom      = Wanderer(seed=seed + 3, period_s=45.0)
        self.w_chromatic  = Wanderer(seed=seed + 4, period_s=20.0)
        self.w_kal        = Wanderer(seed=seed + 5, period_s=25.0)
        self.w_focus      = Wanderer(seed=seed + 6, period_s=40.0)
        self.w_spread     = Wanderer(seed=seed + 7, period_s=35.0)
        self.w_freeze     = Wanderer(seed=seed + 8, period_s=180.0)
        # Counters for telemetry / inspection — the modulator itself
        # is stateless w.r.t. the *output* state, but we expose how
        # often it's been called for logging.
        self.tick_count = 0

    def state(
        self,
        time_s: float,
        features: FastFeatures | None = None,
    ) -> VisualState:
        self.tick_count += 1

        # Audio summary. NaN-safe and `None`-safe so the modulator
        # works even when audio hasn't started yet (cold-boot path).
        if features is not None:
            rms_arr = features.rms or [0.0] * 14
            onset_arr = features.onset_envelope or [0.0] * 14
            n_rms = max(len(rms_arr), 1)
            rms_avg = sum(rms_arr) / n_rms
            onset_max = max(onset_arr) if onset_arr else 0.0
            onset_avg = (sum(onset_arr) / max(len(onset_arr), 1)) if onset_arr else 0.0
        else:
            rms_avg = 0.0
            onset_max = 0.0
            onset_avg = 0.0

        # ---- Palette ---- #

        # Hue drifts across the full circle on its slow wanderer.
        hue = (self.w_hue.value(time_s) + 1.0) * 0.5

        # Saturation: 1.0 baseline, ±0.4 from wanderer, +0.5×rms boost.
        sat = 1.0 + self.w_sat.value(time_s) * 0.4 + rms_avg * 0.5
        sat = _clamp(sat, 0.0, 2.0)

        # ---- Post-FX ---- #

        # Bloom: 0.4 baseline + ±0.25 wanderer + onset boost. Stays in
        # the "tasteful" range; never goes to full washout on its own.
        bloom = 0.4 + self.w_bloom.value(time_s) * 0.25 + onset_avg * 0.3
        bloom = _clamp(bloom, 0.0, 1.0)

        # Chromatic aberration: ramps up only when the wanderer is in
        # its positive half + an audio kick. Most of the time it's 0.
        chrom = max(0.0, self.w_chromatic.value(time_s)) * 0.4 + onset_max * 0.3
        chrom = _clamp(chrom, 0.0, 1.0)

        # Glitch: only kicks in on big onsets. Threshold the per-frame
        # max onset envelope so quiet sections never glitch.
        glitch = max(0.0, onset_max - 0.7) * 1.5
        glitch = _clamp(glitch, 0.0, 1.0)

        # Kaleidoscope: discrete jumps at threshold crossings of a slow
        # wanderer. Most of the time = 1 (off); rare excursions to 3 / 6 / 9.
        k_val = self.w_kal.value(time_s)
        if k_val > 0.6:
            kaleidoscope = 6
        elif k_val > 0.2:
            kaleidoscope = 3
        elif k_val < -0.6:
            kaleidoscope = 9
        else:
            kaleidoscope = 1

        # ---- Channel weights: a "spotlight" wandering across channels ---- #

        # focus_idx ∈ [0, 13] is the centre of attention; spread is the
        # Gaussian σ. Together they pick out a subset of channels at any
        # moment, drifting slowly.
        focus_norm = (self.w_focus.value(time_s) + 1.0) * 0.5
        focus_idx = focus_norm * 13.0
        spread = 2.5 + (self.w_spread.value(time_s) + 1.0) * 3.5  # [2.5, 9.5]
        weights: list[float] = []
        denom = 2.0 * spread * spread
        for i in range(14):
            w = math.exp(-((i - focus_idx) ** 2) / denom)
            # Floor at 0.15 so muted channels never go fully dark — keeps
            # the screen alive even when the spotlight is on the far end.
            weights.append(_clamp(0.15 + w * 0.85, 0.15, 1.0))

        # ---- Transport: rare freeze events ---- #

        # Freeze when the freeze wanderer crosses a high threshold.
        # 180s base period × OCTAVES → freeze events occur at irregular
        # multi-minute spacing, lasting a second or three each.
        freeze = self.w_freeze.value(time_s) > 0.85

        return VisualState(
            channel_weight=weights,
            palette=PaletteState(hue=hue, saturation=sat),
            fx=FxState(
                bloom=bloom,
                glitch=glitch,
                chromatic=chrom,
                kaleidoscope=kaleidoscope,
            ),
            transport=TransportState(freeze=freeze),
        )
