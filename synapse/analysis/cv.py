"""CV (control voltage) extraction per channel.

A "CV" channel on a DC-coupled audio interface (Expert Sleepers ES-9
in particular) carries a slow-moving voltage — typical Eurorack range
is ±5V or 0–10V — that the OS surfaces as `[-1, 1]` audio. We don't
attempt to reverse the sample-rate normalisation; downstream Max
patches handle volt scaling.

Two outputs per CV channel:
  * `value`     — current smoothed DC reading. Single-pole IIR
                  low-pass applied to the per-block mean of the
                  channel, since CV signals don't have meaningful
                  per-sample structure (any AC content would be
                  audio, not CV).
  * `rate`      — first time-derivative (Δvalue / Δt). Useful for
                  detecting LFO peaks / envelope releases / fast
                  knob turns from the Max side. Smoothed too.

The IIR cutoff is configurable but defaults to ~30Hz, which faithfully
captures even fast LFOs while suppressing per-sample dither noise on
the audio interface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CVFeatures:
    """Per-block CV state for the configured CV channels.

    `values` and `rates` are aligned with `channel_indices` (0-based
    indices into the source's full channel array). All length-N where
    N = number of CV channels.
    """

    channel_indices: list[int]
    values: list[float]
    rates: list[float]
    block_count: int = 0
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "cv_channels": list(self.channel_indices),
            "cv_values": list(self.values),
            "cv_rates": list(self.rates),
            "cv_block_count": self.block_count,
        }


class CVDetector:
    """Stateful single-pole IIR low-pass per CV channel.

    The transfer function for a 1-pole IIR with cutoff `f_c` at sample
    rate `f_s` is:
        y[n] = α · x[n] + (1 − α) · y[n−1]
    where `α = 1 − exp(−2π · f_c / f_s)`.

    Block-rate filter: we apply the IIR once per block (not per sample)
    because CV is slow — sub-block detail isn't meaningful. The per-
    block mean of the channel block is the input. With audio sample
    rate 48kHz and block 512, block rate ≈ 94Hz; cutoff f_c=30Hz gives
    α ≈ 0.86. For a slower / smoother CV use lower cutoff (e.g. 5Hz).
    """

    def __init__(
        self,
        cv_channel_indices: list[int],
        block_rate_hz: float,
        cutoff_hz: float = 30.0,
    ) -> None:
        if not cv_channel_indices:
            cv_channel_indices = []
        if block_rate_hz <= 0:
            raise ValueError("block_rate_hz must be > 0")
        if cutoff_hz <= 0 or cutoff_hz >= block_rate_hz / 2:
            raise ValueError(
                f"cutoff_hz {cutoff_hz} must satisfy 0 < f < block_rate/2 = {block_rate_hz/2}"
            )
        self.channel_indices = list(cv_channel_indices)
        self.block_rate_hz = block_rate_hz
        # IIR coefficient. Higher α = less smoothing = faster response.
        self.alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / block_rate_hz)
        # State: smoothed value + previous smoothed value (for rate).
        self._smoothed = np.zeros(len(self.channel_indices), dtype=np.float64)
        self._prev = np.zeros(len(self.channel_indices), dtype=np.float64)
        # Rate is also smoothed (otherwise per-block jitter dominates).
        self._smoothed_rate = np.zeros(len(self.channel_indices), dtype=np.float64)
        self._dt = 1.0 / block_rate_hz

    def process(self, block: np.ndarray, block_count: int = 0) -> CVFeatures:
        """Update state with one new audio block, return current CV state.

        `block` is the full-source-channel-count `(n_channels, n_samples)`
        array; we pick out our configured CV channels by index.
        """
        if not self.channel_indices:
            return CVFeatures(
                channel_indices=[], values=[], rates=[], block_count=block_count
            )
        # Per-block mean for each CV channel (CV has no AC content; mean
        # captures the DC value with built-in averaging across the block).
        block_means = np.array(
            [float(block[ch].mean()) for ch in self.channel_indices],
            dtype=np.float64,
        )
        # IIR step. self._smoothed += alpha * (input - self._smoothed)
        self._prev = self._smoothed.copy()
        self._smoothed += self.alpha * (block_means - self._smoothed)
        # Rate of change. Same IIR coefficient on the *raw* delta so
        # the rate signal isn't an undamped derivative noise floor.
        raw_rate = (self._smoothed - self._prev) / self._dt
        self._smoothed_rate += self.alpha * (raw_rate - self._smoothed_rate)
        return CVFeatures(
            channel_indices=list(self.channel_indices),
            values=[float(v) for v in self._smoothed],
            rates=[float(r) for r in self._smoothed_rate],
            block_count=block_count,
        )
