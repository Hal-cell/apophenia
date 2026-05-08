"""Mailbox for the latest AI-generated frame.

Mirrors the FeatureBus / SlowBus / StateBus single-slot pattern: writers
publish, readers `latest()` get a snapshot — no history, no queue.

A frame is a (H, W, 3) uint8 numpy array (RGB, no alpha — SDXL outputs
RGB and alpha would just be wasted bytes on the GPU upload). Bytes are
held by reference; consumers should treat them as read-only and copy if
they need to mutate.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class AIFrame:
    """One generated frame plus the metadata needed to display + debug it."""

    image: np.ndarray
    """RGB image, shape (H, W, 3), dtype uint8."""

    prompt: str = ""
    """The prompt that produced this frame."""

    gen_count: int = 0
    """Monotonic counter; renderer uses this to detect a fresh frame and
    skip re-uploading the same texture. Starts at 1 on first publish.
    """

    latency_ms: float = 0.0
    """End-to-end generation latency for this frame in milliseconds."""

    seed: int = 0
    """Seed that produced this frame. Useful for reproducibility / debug."""

    model_name: str = ""
    """Model identifier (e.g. 'stabilityai/sdxl-turbo')."""

    extra: dict[str, float] = field(default_factory=dict)
    """Optional per-frame numbers (cfg, num_steps, etc.) for debug logs."""

    def to_dict(self) -> dict[str, object]:
        """JSON-serialisable metadata for the /ws status payload.

        Excludes the raw image — that's far too big to ship over WebSocket
        every frame. UI gets `gen_count` so it can show a "frame N" counter,
        plus latency and prompt for debugging.
        """
        return {
            "prompt": self.prompt,
            "gen_count": self.gen_count,
            "latency_ms": self.latency_ms,
            "seed": self.seed,
            "model_name": self.model_name,
            "image_shape": list(self.image.shape) if self.image is not None else None,
        }


class AIBus:
    """Thread-safe single-slot mailbox holding the most recent AIFrame.

    Producers (the AI worker thread) call `publish`. Consumers (the
    render loop, the WS broadcaster) call `latest()`. A short critical
    section protects the slot; the underlying numpy array is shared by
    reference so consumers must not mutate.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: AIFrame | None = None

    def publish(self, frame: AIFrame) -> None:
        with self._lock:
            self._latest = frame

    def latest(self) -> AIFrame | None:
        with self._lock:
            return self._latest
