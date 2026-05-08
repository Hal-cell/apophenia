"""Per-channel fast features: RMS + peak per audio block.

Phase 1 ships RMS and peak. Phase 2 adds spectral centroid + onset
detection. The contract:

    AudioSource.frames() ──→ fast_features_loop ──→ FeatureBus
                                                       ↓
                                  WebSocket broadcaster (control/server.py)
                                                       ↓
                                                browser meter UI

`FeatureBus` is a single-slot thread-safe mailbox: only the latest
snapshot is kept. UI broadcasts at ~30Hz, audio publishes at ~94Hz
(48kHz/512) — readers losing intermediate snapshots is fine, they
just miss in-between values, never get torn data.
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np

from apophenia.audio.source import AudioSource


@dataclass
class FastFeatures:
    """Snapshot of the latest fast-tier per-channel features.

    Lists are length `n_channels` (14 for our default mock / ES-9 setup).
    Pure-Python types so the dict serialises cleanly to JSON over WebSocket
    without numpy-aware encoding.
    """

    rms: list[float] = field(default_factory=list)
    peak: list[float] = field(default_factory=list)
    block_count: int = 0
    """Number of blocks the worker has processed since open()."""
    timestamp: float = 0.0
    """Monotonic seconds since the worker thread began publishing."""
    source_name: str = ""
    sample_rate: int = 0
    block_size: int = 0
    n_channels: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class FeatureBus:
    """Thread-safe single-slot mailbox for the latest FastFeatures.

    `publish` and `latest` are both O(1) and acquire a mutex briefly. We
    deliberately don't queue history — the UI only ever needs the current
    state, and a queue would just bloat under back-pressure.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: Optional[FastFeatures] = None

    def publish(self, features: FastFeatures) -> None:
        with self._lock:
            self._latest = features

    def latest(self) -> Optional[FastFeatures]:
        with self._lock:
            return self._latest


def compute_block_features(block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel RMS + peak for a `(n_channels, n_samples)` block.

    RMS is computed in float64 to avoid float32 round-off on quiet signals
    (kicks come in at 0.001 RMS sometimes — float32 squaring loses bits).
    Peak is the absolute-max sample value.
    """
    if block.ndim != 2:
        raise ValueError(f"block must be 2D (n_channels, n_samples), got shape {block.shape}")
    rms = np.sqrt(np.mean(block.astype(np.float64) ** 2, axis=1))
    peak = np.max(np.abs(block), axis=1).astype(np.float64)
    return rms, peak


def fast_features_loop(
    source: AudioSource,
    bus: FeatureBus,
    stop_event: threading.Event,
) -> None:
    """Pump audio blocks through compute_block_features and into the bus.

    Designed to run in its own thread. Returns when:
      * `stop_event` is set, OR
      * the source's iterator terminates (file source on a non-looping run), OR
      * the source raises an exception (caller catches via thread join + exc).
    """
    source.open()
    block_count = 0
    t0 = time.monotonic()
    try:
        for block in source.frames():
            if stop_event.is_set():
                break
            block_count += 1
            rms, peak = compute_block_features(block)
            bus.publish(
                FastFeatures(
                    rms=rms.tolist(),
                    peak=peak.tolist(),
                    block_count=block_count,
                    timestamp=time.monotonic() - t0,
                    source_name=type(source).__name__,
                    sample_rate=source.sample_rate,
                    block_size=source.block_size,
                    n_channels=source.n_channels,
                )
            )
    finally:
        source.close()
