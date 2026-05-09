"""Per-channel log-spaced spectrum bins.

Audio channels (`ChannelRole.AUDIO`) get a 32-bin log-spaced magnitude
spectrum at a throttled output rate (default ~30Hz, vs the audio
block rate of ~94Hz at 48kHz/512).

Why throttle:
    Per-block sending of 32 floats × N channels at 94Hz is fine on
    localhost UDP, but the human eye / Unreal frame loop can't use
    >30Hz spectral motion meaningfully — and downsampling at the
    sender keeps Max's [route] / `[zl] / `[unpack]` workload down.

Why log-spaced:
    Linear FFT bins waste resolution at the top end (bin 0 = 0Hz,
    bin 1 = ~94Hz, bin 256 = nyquist) and starve the bass. Log-
    spaced bins from ~20Hz to nyquist match human pitch perception
    and modular-synth frequency content distribution.

Why magnitude (not dB / power):
    Linear magnitude with optional soft compression (tanh) gives
    a value in [0, 1] that drives visual mappings directly. Max
    can compute log-units after the fact if a particular patch
    wants them.

Output is a `SpectrumFeatures` dataclass with a `(n_audio_channels,
n_bins)` flat-Python list. `process()` returns `None` between throttle
boundaries — the caller can either skip OSC for those blocks or
re-send the last frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SpectrumFeatures:
    """One spectrum frame, throttled at the configured output rate.

    `bins` is a list of length `len(channel_indices)`, each inner list
    has `n_bins` floats in roughly [0, 1]. `bin_edges_hz` is the
    `n_bins + 1` frequency edges defining each bin (informational —
    Max consumers can ignore it; they just need to know the bins are
    log-spaced from `fmin_hz` to nyquist).
    """

    channel_indices: list[int]
    bins: list[list[float]]
    bin_edges_hz: list[float]
    block_count: int = 0

    @property
    def n_bins(self) -> int:
        return len(self.bin_edges_hz) - 1 if self.bin_edges_hz else 0

    def to_dict(self) -> dict[str, object]:
        return {
            "spectrum_channels": list(self.channel_indices),
            "spectrum_bins": [list(row) for row in self.bins],
            "spectrum_bin_edges_hz": list(self.bin_edges_hz),
            "spectrum_block_count": self.block_count,
        }

    def filter_to(self, allowed_channels: set[int]) -> SpectrumFeatures:
        """Return a copy keeping only entries whose channel index is in
        `allowed_channels`. Used for live role-switching — channels no
        longer in audio role drop out of the next emission, channels
        newly in audio role re-appear with whatever bins the detector
        had on its last throttle boundary."""
        keep = [i for i, ch in enumerate(self.channel_indices) if ch in allowed_channels]
        return SpectrumFeatures(
            channel_indices=[self.channel_indices[i] for i in keep],
            bins=[list(self.bins[i]) for i in keep],
            bin_edges_hz=list(self.bin_edges_hz),
            block_count=self.block_count,
        )


class SpectrumDetector:
    """Stateful Hann-windowed FFT → log-spaced bins, throttled.

    One detector instance handles all configured audio channels and
    emits a single `SpectrumFeatures` snapshot when the throttle
    boundary fires. Between boundaries `process()` returns `None`.

    Throttle resolution is one block — i.e. effective output rate is
    `block_rate / round(block_rate / output_hz)`. For 94Hz block rate
    + 30Hz target, stride = round(94/30) = 3, effective output ≈ 31Hz.

    Compression:
      Magnitude per bin is normalised by the number of FFT bins
      contributing to it (so wider bins at the top don't dominate),
      then `np.tanh(compression * value)` is applied for soft clipping
      into [0, 1]. With `compression = 0.0` (default), the tanh is
      skipped and raw magnitude per FFT bin (averaged) is returned.
    """

    DEFAULT_N_BINS = 32
    DEFAULT_OUTPUT_HZ = 30.0
    DEFAULT_FMIN_HZ = 20.0
    DEFAULT_COMPRESSION = 8.0

    def __init__(
        self,
        audio_channel_indices: list[int],
        sample_rate: int,
        block_size: int,
        n_bins: int = DEFAULT_N_BINS,
        output_hz: float = DEFAULT_OUTPUT_HZ,
        fmin_hz: float = DEFAULT_FMIN_HZ,
        compression: float = DEFAULT_COMPRESSION,
    ) -> None:
        if sample_rate <= 0 or block_size <= 0:
            raise ValueError("sample_rate / block_size must be > 0")
        if n_bins <= 0:
            raise ValueError("n_bins must be > 0")
        if output_hz <= 0:
            raise ValueError("output_hz must be > 0")
        nyquist = sample_rate / 2.0
        if fmin_hz <= 0 or fmin_hz >= nyquist:
            raise ValueError(
                f"fmin_hz {fmin_hz} must satisfy 0 < f < nyquist ({nyquist})"
            )
        if compression < 0:
            raise ValueError("compression must be >= 0")

        self.channel_indices = list(audio_channel_indices)
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.n_bins = n_bins
        self.compression = compression

        # Throttle: emit every Nth block where N rounds block_rate to output_hz.
        block_rate = sample_rate / block_size
        self.stride = max(1, int(round(block_rate / output_hz)))

        # Pre-compute log-spaced bin edges and which FFT bins fall in each.
        self.bin_edges_hz = np.geomspace(fmin_hz, nyquist, n_bins + 1).tolist()
        fft_freqs = np.fft.rfftfreq(block_size, d=1.0 / sample_rate)
        # For each output bin, the start/stop indices (slice) into fft_freqs.
        self._bin_slices: list[tuple[int, int]] = []
        for i in range(n_bins):
            lo, hi = self.bin_edges_hz[i], self.bin_edges_hz[i + 1]
            # Inclusive lo, exclusive hi (so adjacent bins don't double-count).
            mask = (fft_freqs >= lo) & (fft_freqs < hi)
            indices = np.where(mask)[0]
            if len(indices) == 0:
                # Empty bin (happens at the very low end if bins are
                # narrower than 1/N rate). Use the nearest single FFT
                # bin as a fallback so we don't emit zeros for live
                # bass content.
                centre = (lo + hi) * 0.5
                nearest = int(np.argmin(np.abs(fft_freqs - centre)))
                self._bin_slices.append((nearest, nearest + 1))
            else:
                self._bin_slices.append((int(indices[0]), int(indices[-1]) + 1))

        # Pre-computed Hann window for FFT framing.
        self._window = np.hanning(block_size).astype(np.float32)

        # Block-stride counter (advances every process() call regardless
        # of whether we emit, so emission alignment is purely modular).
        self._block_count_since_emit = 0
        # Sticky last-emitted frame, kept for callers that want to
        # forward "the latest known spectrum" between throttle boundaries.
        self._last: SpectrumFeatures | None = None

    @property
    def output_hz_effective(self) -> float:
        """Actual output rate given block-aligned throttling."""
        return (self.sample_rate / self.block_size) / self.stride

    def latest(self) -> SpectrumFeatures | None:
        """Most recent emitted frame, or None if we haven't emitted yet."""
        return self._last

    def process(self, block: np.ndarray, block_count: int = 0) -> SpectrumFeatures | None:
        """Maybe compute and return a spectrum frame.

        Returns `None` between throttle boundaries (most blocks).
        Returns a fresh `SpectrumFeatures` on the boundary block.
        """
        if not self.channel_indices:
            return None

        self._block_count_since_emit += 1
        if self._block_count_since_emit < self.stride:
            return None
        self._block_count_since_emit = 0

        # Compute windowed magnitude FFT for our audio channels only.
        ch_block = block[self.channel_indices].astype(np.float64)
        windowed = ch_block * self._window
        spec = np.fft.rfft(windowed, axis=1)
        mag = np.abs(spec) / self.block_size  # Per-sample-equivalent magnitude.

        # Bucket into output bins (mean of contributing FFT bins per output bin).
        out = np.zeros((len(self.channel_indices), self.n_bins), dtype=np.float64)
        for i, (start, stop) in enumerate(self._bin_slices):
            out[:, i] = mag[:, start:stop].mean(axis=1)

        # Optional soft compression to [0, 1]-ish range.
        if self.compression > 0.0:
            out = np.tanh(out * self.compression)

        features = SpectrumFeatures(
            channel_indices=list(self.channel_indices),
            bins=[row.tolist() for row in out],
            bin_edges_hz=list(self.bin_edges_hz),
            block_count=block_count,
        )
        self._last = features
        return features
