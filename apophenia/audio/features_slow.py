"""Slow-tier features: CLAP audio embedding + mood projection (~1Hz).

CLAP (Contrastive Language-Audio Pretraining) is a model that embeds an
audio clip into a 512-dim vector aligned with text-embedding space.
That vector is what a downstream image model (phase 6 SDXL-Turbo) will
condition on alongside text prompts. We compute it once per second on
a 1-second sliding window of the multichannel input summed to mono.

Why a separate worker:
    The fast-tier loop runs ~94Hz on tiny blocks. CLAP inference takes
    30-200ms depending on hardware — that would absolutely glitch the
    audio thread if run inline. The architecture instead splits:

      fast_features_loop ──┐                  AudioBuffer (ring)
                           ├──→  fast block ──┘
                                              │
                                              ▼ slow worker reads
                                      slow_features_loop @ 1Hz
                                              │
                                              ▼
                                       SlowBus (latest snapshot)

Mood projection (valence/arousal) is stubbed — a real implementation
needs a labelled training set. V1 ships zeros and documents the gap;
the AI engine in phase 6 conditions on the raw embedding, which is
what actually matters.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from apophenia.audio.source import AudioSource

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Tuning
# --------------------------------------------------------------------------- #

CLAP_EMBED_DIM = 512
"""LAION-CLAP audio_features output dimensionality."""

CLAP_WINDOW_SECONDS = 1.0
"""How much recent audio CLAP gets fed each inference. The model was
trained on 10s clips; 1s gives reasonable embeddings for "what's
happening right now" while keeping latency low."""

CLAP_PERIOD_SECONDS = 1.0
"""How often we run inference. 1Hz is plenty for visual conditioning."""

CLAP_MODEL_NAME = "laion/clap-htsat-unfused"
"""HuggingFace model id. ~600MB download on first run; cached after.

Alternatives:
  laion/clap-htsat-fused           ~same, fused checkpoint (deprecated path)
  laion/larger_clap_general        bigger, slower, marginal improvement
  laion/larger_clap_music          music-specialised
"""

CLAP_SAMPLE_RATE = 48_000
"""LAION-CLAP defaults to 48kHz audio. Matches our pipeline rate, so
no resampling is needed."""


# --------------------------------------------------------------------------- #
# SlowFeatures + SlowBus
# --------------------------------------------------------------------------- #


@dataclass
class SlowFeatures:
    """Snapshot of the latest slow-tier audio understanding.

    Floats are pure-Python so the dict serialises cleanly to JSON over
    WebSocket. The 512-dim embedding adds ~3-4KB per WS message, which
    is fine on localhost but worth knowing.
    """

    clap_embedding: list[float] = field(default_factory=list)
    """Length-CLAP_EMBED_DIM vector from CLAP's audio encoder."""

    valence: float = 0.0
    """[-1, 1]. Stubbed — phase 4 ships zeros; real projection is V1.x."""
    arousal: float = 0.0

    update_count: int = 0
    """Number of CLAP inferences run so far."""
    timestamp: float = 0.0
    """Monotonic seconds since the slow worker started."""
    inference_ms: float = 0.0
    """Wall-clock duration of the most recent CLAP forward pass."""
    embedding_norm: float = 0.0
    """L2 norm of the latest embedding. Useful sanity check / display."""
    model_name: str = ""
    """Which HuggingFace model produced these features."""

    def to_dict(self) -> dict:
        return asdict(self)


class SlowBus:
    """Thread-safe single-slot mailbox for the latest SlowFeatures.

    Same shape as FeatureBus from features_fast — only the latest
    snapshot is kept; readers losing intermediate snapshots is fine
    because slow features evolve gradually.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: SlowFeatures | None = None

    def publish(self, features: SlowFeatures) -> None:
        with self._lock:
            self._latest = features

    def latest(self) -> SlowFeatures | None:
        with self._lock:
            return self._latest


# --------------------------------------------------------------------------- #
# AudioBuffer — shared ring between fast and slow workers
# --------------------------------------------------------------------------- #


class AudioBuffer:
    """Thread-safe multichannel ring buffer for "the last N seconds".

    The fast feature worker writes blocks as they arrive. The slow
    worker reads a contiguous window via `tail()` whenever it needs a
    fresh CLAP input. Lock-protected so writes never tear; reads return
    a copy so the caller can free the lock fast.
    """

    def __init__(
        self,
        n_channels: int,
        sample_rate: int,
        duration_s: float = CLAP_WINDOW_SECONDS * 2,
    ) -> None:
        self.n_channels = n_channels
        self.sample_rate = sample_rate
        self.n_samples = int(sample_rate * duration_s)
        self._buf = np.zeros((n_channels, self.n_samples), dtype=np.float32)
        self._write_pos = 0
        self._lock = threading.Lock()
        self.total_samples_written = 0

    def write(self, block: np.ndarray) -> None:
        """Append a (n_channels, n_samples) block to the ring."""
        if block.shape[0] != self.n_channels:
            raise ValueError(
                f"block has {block.shape[0]} channels, buffer expects {self.n_channels}"
            )
        n = block.shape[1]
        if n > self.n_samples:
            raise ValueError(
                f"block size {n} exceeds buffer capacity {self.n_samples}"
            )
        with self._lock:
            end = self._write_pos + n
            if end <= self.n_samples:
                self._buf[:, self._write_pos:end] = block
            else:
                head = self.n_samples - self._write_pos
                self._buf[:, self._write_pos:] = block[:, :head]
                self._buf[:, : n - head] = block[:, head:]
            self._write_pos = end % self.n_samples
            self.total_samples_written += n

    def tail(self, n_samples: int) -> np.ndarray:
        """Return the most recent `n_samples` in chronological order.

        Returns a fresh array (copy from the ring), not a view, so the
        caller is free to do anything with it without holding the lock.
        """
        if n_samples > self.n_samples:
            raise ValueError(
                f"requested tail of {n_samples} exceeds buffer capacity {self.n_samples}"
            )
        with self._lock:
            start = (self._write_pos - n_samples) % self.n_samples
            if start + n_samples <= self.n_samples:
                return self._buf[:, start:start + n_samples].copy()
            head = self.n_samples - start
            out = np.empty((self.n_channels, n_samples), dtype=np.float32)
            out[:, :head] = self._buf[:, start:]
            out[:, head:] = self._buf[:, : n_samples - head]
            return out


# --------------------------------------------------------------------------- #
# CLAP encoder
# --------------------------------------------------------------------------- #


class ClapEncoder:
    """Thin wrapper around HuggingFace's ClapModel that does mono-window
    inference on demand. Loads lazily so importing features_slow doesn't
    pull in torch / transformers up front — only `--no-clap` users still
    pay zero startup cost.
    """

    def __init__(
        self,
        model_name: str = CLAP_MODEL_NAME,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self._device = device  # resolved at load time
        self._model: Any = None
        self._processor: Any = None
        self._loaded = False

    def load(self) -> None:
        """Download (first run) + initialise the model. Blocking; expect
        20-60s on first call as ~600MB downloads and PyTorch warms up.
        """
        if self._loaded:
            return
        import torch
        from transformers import ClapModel, ClapProcessor

        # Resolve device. MPS is available on Apple Silicon Pythons built
        # against the right wheels (torch ≥ 2.0); falls back to CPU.
        if self._device is None:
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

        logger.info("loading CLAP %r onto device=%s", self.model_name, self._device)
        t0 = time.monotonic()
        self._processor = ClapProcessor.from_pretrained(self.model_name)
        model = ClapModel.from_pretrained(self.model_name)
        # `eval()` disables dropout etc.; we never train.
        model.eval()
        # MPS sometimes barfs on float16 ops; stick with float32 unless
        # benchmarks say otherwise.
        model = model.to(self._device)
        self._model = model
        self._loaded = True
        logger.info("CLAP loaded in %.1fs", time.monotonic() - t0)

    def encode(self, audio_mono: np.ndarray, sample_rate: int) -> np.ndarray:
        """Run one inference on a 1-D float32 audio array.

        Returns a (CLAP_EMBED_DIM,) float32 numpy array. Caller is
        responsible for downmixing multichannel input first.
        """
        if not self._loaded:
            self.load()
        import torch

        assert self._model is not None and self._processor is not None
        if audio_mono.ndim != 1:
            raise ValueError(f"audio_mono must be 1-D, got shape {audio_mono.shape}")

        # transformers ≥ 5.0 renamed the audio kwarg from `audios` →
        # `audio`. Fall back to the old name on older releases.
        try:
            inputs = self._processor(
                audio=audio_mono,
                sampling_rate=sample_rate,
                return_tensors="pt",
            )
        except (TypeError, ValueError):
            inputs = self._processor(
                audios=audio_mono,
                sampling_rate=sample_rate,
                return_tensors="pt",
            )
        # Move all input tensors to the model's device.
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            output = self._model.get_audio_features(**inputs)
        # transformers 5.x wraps the embedding in a BaseModelOutput; older
        # releases returned the raw tensor. Unwrap if needed.
        if hasattr(output, "pooler_output") and output.pooler_output is not None:
            tensor = output.pooler_output
        elif hasattr(output, "last_hidden_state"):
            tensor = output.last_hidden_state
        else:
            tensor = output  # legacy: raw tensor
        # tensor shape: (batch=1, CLAP_EMBED_DIM). Move to CPU before numpy.
        return tensor.detach().to("cpu").numpy()[0]


# --------------------------------------------------------------------------- #
# Worker loop
# --------------------------------------------------------------------------- #


def slow_features_loop(
    source: AudioSource,
    audio_buffer: AudioBuffer,
    bus: SlowBus,
    stop_event: threading.Event,
    encoder: ClapEncoder | None = None,
    period_s: float = CLAP_PERIOD_SECONDS,
    window_s: float = CLAP_WINDOW_SECONDS,
) -> None:
    """Periodically pull a `window_s`-second tail from `audio_buffer`,
    sum to mono, run CLAP, publish to `bus`. Sleeps the rest of the
    `period_s` interval in between.

    `encoder` defaults to a real `ClapEncoder` but tests inject a mock.
    """
    if encoder is None:
        encoder = ClapEncoder()

    window_samples = int(source.sample_rate * window_s)
    if window_samples > audio_buffer.n_samples:
        raise ValueError(
            f"audio_buffer too small for {window_s}s window at {source.sample_rate}Hz"
        )

    # Block until the buffer has at least one full window so we don't
    # send mostly-zeros to CLAP on startup.
    needed = window_samples
    while not stop_event.is_set():
        if audio_buffer.total_samples_written >= needed:
            break
        time.sleep(0.05)
    if stop_event.is_set():
        return

    update_count = 0
    t0 = time.monotonic()
    next_run = time.monotonic()
    while not stop_event.is_set():
        now = time.monotonic()
        sleep_for = next_run - now
        if sleep_for > 0:
            # Wake early on stop_event so shutdown is prompt.
            stopped = stop_event.wait(timeout=sleep_for)
            if stopped:
                break
        next_run = time.monotonic() + period_s

        try:
            window = audio_buffer.tail(window_samples)
        except ValueError:
            logger.exception("audio buffer tail() failed")
            continue
        # Sum to mono. Mean rather than sum so we don't clip on dense
        # multichannel input.
        mono = window.mean(axis=0).astype(np.float32, copy=False)

        try:
            t_start = time.monotonic()
            embed = encoder.encode(mono, source.sample_rate)
            inf_ms = (time.monotonic() - t_start) * 1000.0
        except Exception as e:  # noqa: BLE001
            logger.exception("CLAP inference failed: %s", e)
            continue

        update_count += 1
        norm = float(np.linalg.norm(embed))
        bus.publish(
            SlowFeatures(
                clap_embedding=embed.astype(np.float32).tolist(),
                valence=0.0,  # TODO: real projection in V1.x
                arousal=0.0,
                update_count=update_count,
                timestamp=time.monotonic() - t0,
                inference_ms=inf_ms,
                embedding_norm=norm,
                model_name=encoder.model_name,
            )
        )
        logger.info(
            "CLAP update %d: %.1fms, ‖z‖=%.2f",
            update_count,
            inf_ms,
            norm,
        )
