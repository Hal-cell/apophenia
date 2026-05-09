"""Per-channel fast features: RMS, peak, spectral centroid, onset envelope.

Phase 2 surface adds centroid (Hann-windowed FFT) and onset detection
(energy-ratio + refractory window + decay envelope). All four feature
arrays land in `FastFeatures` and ride the same `FeatureBus` /
WebSocket path.

The onset signal is published as a per-channel **envelope** (float in
[0, 1]) rather than a boolean. The audio loop runs ~94Hz (48kHz/512)
but the WebSocket broadcaster reads at 30Hz; if onsets were booleans
we'd routinely miss them in the polling gap. The envelope rises to 1.0
on a fresh trigger and decays geometrically each block, so any onset
within the last ~30ms is still visible to the UI as a non-zero value.

Pipeline:

    AudioSource.frames()  ──→  fast_features_loop  ──→  FeatureBus
                                                            ↓
                                  WebSocket broadcaster (control/server.py)
                                                            ↓
                                                    browser meter UI
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field

import numpy as np

from synapse.audio.source import AudioSource

# --------------------------------------------------------------------------- #
# Tuning constants
# --------------------------------------------------------------------------- #

ONSET_THRESHOLD = 1.5
"""Onset fires when current_rms / smoothed_rms exceeds this ratio."""

ONSET_FLOOR = 0.005
"""Below this RMS we treat the channel as silent and never fire onsets;
keeps room-tone / DC offset from triggering false positives."""

ONSET_SMOOTH_HZ = 4.0
"""Cutoff frequency of the one-pole low-pass that builds the
'baseline RMS' an incoming block is compared against. Slow enough that
sustained loud passages don't suppress new onsets; fast enough that the
baseline catches up after a quiet stretch."""

ONSET_REFRACTORY_MS = 50.0
"""After an onset fires, suppress further onsets on that channel for
this many milliseconds. Stops one drum hit firing 2-3 onsets across
adjacent blocks."""

ONSET_DECAY_PER_BLOCK = 0.7
"""Multiplied into the envelope each block. 0.7 → halves every ~2
blocks (≈21ms at 48kHz/512). Means a fired envelope is still ~0.5 by
the time the next 30Hz UI poll lands."""


# --------------------------------------------------------------------------- #
# FastFeatures + FeatureBus
# --------------------------------------------------------------------------- #


@dataclass
class FastFeatures:
    """Snapshot of the latest fast-tier per-channel features.

    Lists are length `n_channels`. Pure-Python types so the dict
    serialises cleanly to JSON over WebSocket.
    """

    rms: list[float] = field(default_factory=list)
    peak: list[float] = field(default_factory=list)
    centroid: list[float] = field(default_factory=list)
    """Spectral centroid in Hz, per channel. 0 for silent channels."""
    onset_envelope: list[float] = field(default_factory=list)
    """Decaying onset indicator in [0, 1], per channel. 1.0 = onset
    just fired this block; decays each block by ONSET_DECAY_PER_BLOCK."""

    block_count: int = 0
    timestamp: float = 0.0
    source_name: str = ""
    sample_rate: int = 0
    block_size: int = 0
    n_channels: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class FeatureBus:
    """Thread-safe single-slot mailbox for the latest FastFeatures."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: FastFeatures | None = None

    def publish(self, features: FastFeatures) -> None:
        with self._lock:
            self._latest = features

    def latest(self) -> FastFeatures | None:
        with self._lock:
            return self._latest


# --------------------------------------------------------------------------- #
# Stateless block features (RMS, peak, centroid)
# --------------------------------------------------------------------------- #


def make_window(block_size: int) -> np.ndarray:
    """Return a Hann window for FFT framing, cached at the call site.

    Hann reduces spectral leakage so centroid measurements don't bias
    toward DC for pure tones. We pre-compute once per worker rather than
    rebuild every block.
    """
    return np.hanning(block_size).astype(np.float32)


def compute_block_features(
    block: np.ndarray,
    sample_rate: int,
    window: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute (rms, peak, centroid) for a `(n_channels, n_samples)` block.

    All outputs are length-`n_channels` float64 arrays:
      * rms       — root-mean-square in [0, ~1.5]
      * peak      — abs-max sample value, used by the UI peak-hold line
      * centroid  — spectral centroid in Hz; 0 for near-silent channels

    The window argument is a pre-computed Hann window of length
    `n_samples`; pass one in to avoid recomputing every call. If None,
    a fresh window is allocated.
    """
    if block.ndim != 2:
        raise ValueError(f"block must be 2D (n_channels, n_samples), got shape {block.shape}")
    n_channels, n_samples = block.shape
    if window is None:
        window = make_window(n_samples)
    elif len(window) != n_samples:
        raise ValueError(
            f"window length {len(window)} doesn't match block n_samples {n_samples}"
        )

    block64 = block.astype(np.float64)
    rms = np.sqrt(np.mean(block64**2, axis=1))
    peak = np.max(np.abs(block64), axis=1)

    # Spectral centroid via Hann-windowed rfft. mag has shape
    # (n_channels, n_bins). freqs is (n_bins,) — broadcasts on axis 1.
    windowed = block64 * window
    spec = np.fft.rfft(windowed, axis=1)
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
    sum_mag = mag.sum(axis=1)
    sum_fmag = (mag * freqs).sum(axis=1)
    # Channels below ONSET_FLOOR get centroid 0 — otherwise division
    # surfaces noise-floor garbage.
    centroid = np.where(
        sum_mag > 1e-9,
        sum_fmag / np.maximum(sum_mag, 1e-12),
        0.0,
    )
    centroid = np.where(rms > ONSET_FLOOR, centroid, 0.0)

    return rms, peak, centroid


# --------------------------------------------------------------------------- #
# Stateful onset detection (with envelope)
# --------------------------------------------------------------------------- #


class OnsetDetector:
    """Per-channel energy-ratio onset detection with refractory + envelope.

    Algorithm:
      1. Maintain a one-pole low-passed `smoothed_rms` per channel
         (cutoff ≈ ONSET_SMOOTH_HZ).
      2. Each block:
         a. Trigger an onset if `rms > floor` AND `rms / smoothed > ratio`,
            unless we're inside the per-channel refractory window.
         b. Update the envelope: multiply by ONSET_DECAY_PER_BLOCK,
            then set to 1.0 wherever a fresh onset fired.
         c. Update `smoothed_rms` toward the current rms.
      3. Return the envelope (float [0, 1] per channel).
    """

    def __init__(
        self,
        n_channels: int,
        sample_rate: int,
        block_size: int,
        threshold: float = ONSET_THRESHOLD,
        floor: float = ONSET_FLOOR,
        smooth_hz: float = ONSET_SMOOTH_HZ,
        refractory_ms: float = ONSET_REFRACTORY_MS,
        decay_per_block: float = ONSET_DECAY_PER_BLOCK,
    ) -> None:
        self.n_channels = n_channels
        self.threshold = threshold
        self.floor = floor
        self.decay = decay_per_block

        # One-pole coefficient: alpha = 1 - exp(-2π · cutoff · dt). At
        # block_size=512, sr=48000, smooth_hz=4 → alpha ≈ 0.27.
        dt = block_size / sample_rate
        self.smooth_alpha = float(1 - np.exp(-2 * np.pi * smooth_hz * dt))

        # Refractory expressed in *block counts* so per-channel timestamping
        # only needs an integer compare, no clock arithmetic in the loop.
        self.refractory_blocks = max(1, int(round(refractory_ms / 1000.0 / dt)))

        self.smoothed = np.zeros(n_channels, dtype=np.float64)
        self.envelope = np.zeros(n_channels, dtype=np.float64)
        self.last_onset_block = np.full(n_channels, -10_000, dtype=np.int64)
        self.block_count = 0

    def update(self, rms: np.ndarray) -> np.ndarray:
        """Process one block's RMS, return per-channel onset envelope."""
        self.block_count += 1

        # Decay first so a fresh onset clamps to 1.0 cleanly below.
        self.envelope *= self.decay

        # Trigger detection: ratio > threshold AND above floor AND past refractory.
        ratio = rms / np.maximum(self.smoothed, 1e-9)
        candidates = (rms > self.floor) & (ratio > self.threshold)
        # Refractory check (vectorised).
        not_refractory = (self.block_count - self.last_onset_block) >= self.refractory_blocks
        fired = candidates & not_refractory

        if np.any(fired):
            self.envelope[fired] = 1.0
            self.last_onset_block[fired] = self.block_count

        # Update smoothed AFTER detection so an attack block doesn't
        # immediately suppress its own ratio test.
        self.smoothed = (1.0 - self.smooth_alpha) * self.smoothed + self.smooth_alpha * rms

        return self.envelope.copy()


# --------------------------------------------------------------------------- #
# Worker loop
# --------------------------------------------------------------------------- #


def fast_features_loop(
    source: AudioSource,
    bus: FeatureBus,
    stop_event: threading.Event,
    audio_buffer: object | None = None,
    cv_detector: object | None = None,
    gate_detector: object | None = None,
    osc_sender: object | None = None,
) -> None:
    """Pump audio blocks through feature extraction and into the bus.

    Runs in its own thread. Returns when stop_event is set, the source's
    iterator terminates (file source on a non-looping run), or the source
    raises.

    Optional detectors / outputs:
      * `audio_buffer` — an `AudioBuffer` (from features_slow) that the
        slow CLAP worker reads from. Each block also gets written here.
      * `cv_detector`  — a `CVDetector` for slow DC value extraction.
      * `gate_detector` — a `GateDetector` for Schmitt-triggered binary
        state + edge events.
      * `osc_sender`   — an `OSCSender` that ships every block's
        features as one OSC bundle to MaxMSP / any UDP listener.

    All four params are typed `object` to keep features_fast cheap to
    import — they live in sibling packages with their own deps that we
    don't want this module pulling in transitively.
    """
    source.open()
    block_count = 0
    t0 = time.monotonic()
    window = make_window(source.block_size)
    detector = OnsetDetector(
        n_channels=source.n_channels,
        sample_rate=source.sample_rate,
        block_size=source.block_size,
    )
    try:
        for block in source.frames():
            if stop_event.is_set():
                break
            block_count += 1
            if audio_buffer is not None:
                audio_buffer.write(block)  # type: ignore[attr-defined]
            rms, peak, centroid = compute_block_features(block, source.sample_rate, window=window)
            envelope = detector.update(rms)
            fast_features = FastFeatures(
                rms=rms.tolist(),
                peak=peak.tolist(),
                centroid=centroid.tolist(),
                onset_envelope=envelope.tolist(),
                block_count=block_count,
                timestamp=time.monotonic() - t0,
                source_name=type(source).__name__,
                sample_rate=source.sample_rate,
                block_size=source.block_size,
                n_channels=source.n_channels,
            )
            bus.publish(fast_features)

            cv_features = (
                cv_detector.process(block, block_count)  # type: ignore[attr-defined]
                if cv_detector is not None else None
            )
            gate_features = (
                gate_detector.process(block, block_count)  # type: ignore[attr-defined]
                if gate_detector is not None else None
            )

            if osc_sender is not None:
                osc_sender.send_block(  # type: ignore[attr-defined]
                    fast_features, cv=cv_features, gate=gate_features,
                )
    finally:
        source.close()


