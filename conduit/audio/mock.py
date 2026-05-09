"""Synthetic 14-channel audio source for hardware-free development.

Six patterns generate different signal shapes useful for testing different
parts of the pipeline (level meter, onset detection, AI conditioning, etc.).
All patterns are deterministic given the seed, so visual regression tests
can rely on them.

See `spec/audio-sources.md` (vault) for the full pattern catalogue.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

PATTERNS = ("silence", "sines", "drums", "melody", "chaos", "single")
N_CHANNELS = 14


class MockSource:
    """Deterministic 14-channel synthetic audio.

    Args:
        pattern: one of `PATTERNS`. Unknown values fall back to 'silence'
                 with a warning printed once at open().
        sample_rate: 48 kHz default.
        block_size: 512 samples default (~10.7 ms at 48 kHz).
        bpm: tempo for rhythmic patterns (drums, melody).
        seed: RNG seed for the noisy patterns (chaos / single envelopes).
    """

    n_channels: int = N_CHANNELS
    sample_rate: int
    block_size: int

    def __init__(
        self,
        pattern: str = "silence",
        sample_rate: int = 48_000,
        block_size: int = 512,
        bpm: float = 120.0,
        seed: int = 42,
    ) -> None:
        self.pattern = pattern if pattern in PATTERNS else "silence"
        self._unknown_pattern_warning = pattern not in PATTERNS
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.bpm = bpm
        self._rng = np.random.default_rng(seed)
        self._sample_pos = 0  # samples elapsed since open()
        self._opened = False
        self._closed = False

    # ------------------------------------------------------------------ #
    # AudioSource Protocol surface
    # ------------------------------------------------------------------ #

    def open(self) -> None:
        if self._unknown_pattern_warning:
            import warnings

            warnings.warn(
                f"unknown mock pattern; falling back to 'silence'. "
                f"valid patterns: {PATTERNS}",
                stacklevel=2,
            )
        self._opened = True

    def close(self) -> None:
        self._closed = True

    def frames(self) -> Iterator[np.ndarray]:
        if not self._opened:
            self.open()
        block_period = self.block_size / self.sample_rate
        next_emit = time.monotonic()
        while not self._closed:
            block = self._generate_block()
            self._sample_pos += self.block_size
            yield block
            next_emit += block_period
            sleep = next_emit - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
            else:
                # We're behind real-time; reset pacing so we don't spiral.
                next_emit = time.monotonic()

    # ------------------------------------------------------------------ #
    # Pattern generators
    # ------------------------------------------------------------------ #

    def _generate_block(self) -> np.ndarray:
        block = np.zeros((N_CHANNELS, self.block_size), dtype=np.float32)
        if self.pattern == "silence":
            return block

        # Sample-time array for this block (seconds since open()).
        t_start = self._sample_pos / self.sample_rate
        t = t_start + np.arange(self.block_size, dtype=np.float32) / self.sample_rate

        if self.pattern == "sines":
            # 14 different frequencies, 110Hz × 2^(ch/12) — A2 climbing semitones.
            for ch in range(N_CHANNELS):
                freq = 110.0 * 2.0 ** (ch / 12.0)
                block[ch] = 0.3 * np.sin(2 * np.pi * freq * t)
            return block

        if self.pattern == "single":
            # ch1 only: 220Hz sine with slow envelope; rest silent.
            env = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t)  # 0.25 Hz LFO
            block[0] = (0.4 * env * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)
            return block

        if self.pattern == "drums":
            beat = 60.0 / self.bpm  # seconds per beat
            # ch1 kick (every beat), ch2 snare (off-beat), ch3 hihat (8ths),
            # ch4–8 perc rolls, ch9–14 silent.
            block[0] = self._impulse_train(t, period=beat, decay=0.10, freq=60.0)
            block[1] = self._impulse_train(t, period=beat, offset=beat / 2, decay=0.05, freq=200.0, noise_blend=0.5)
            block[2] = self._impulse_train(t, period=beat / 2, decay=0.02, freq=8000.0, noise_blend=0.9)
            for ch in range(3, 8):
                block[ch] = self._impulse_train(
                    t,
                    period=beat / 4,
                    offset=ch * 0.05,
                    decay=0.03,
                    freq=300.0 + ch * 200.0,
                    noise_blend=0.4,
                )
            return block

        if self.pattern == "melody":
            # ch1–4: sine "notes" stepping through a D-minor scale every beat.
            # ch5–8: slow pad (LFO-modulated saws).
            # ch9–14: occasional bursts of noise (FX).
            beat = 60.0 / self.bpm
            scale = np.array([146.83, 164.81, 174.61, 196.0, 220.0, 246.94, 261.63])  # D3 dorian-ish
            for ch in range(4):
                step = int((self._sample_pos / self.sample_rate) / beat) + ch * 2
                freq = scale[step % len(scale)] * (1 + 0.5 * ch)
                env = self._impulse_train(t, period=beat, decay=0.3, freq=freq)
                block[ch] = 0.3 * env
            for ch in range(4, 8):
                lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t + ch)
                saw = 2 * (t * (60 + ch * 5) - np.floor(0.5 + t * (60 + ch * 5)))
                block[ch] = (0.15 * lfo * saw).astype(np.float32)
            for ch in range(8, N_CHANNELS):
                # Random short bursts; rng is seeded so determinism holds.
                if self._rng.random() < 0.02:
                    burst = self._rng.standard_normal(self.block_size).astype(np.float32) * 0.2
                    block[ch] = burst
            return block

        if self.pattern == "chaos":
            # Independent white-noise per channel × slow LFO envelopes.
            for ch in range(N_CHANNELS):
                lfo = 0.4 + 0.6 * np.sin(2 * np.pi * (0.2 + 0.1 * ch) * t + ch)
                noise = self._rng.standard_normal(self.block_size).astype(np.float32)
                block[ch] = (0.3 * lfo * noise).astype(np.float32)
            return block

        # Fallthrough: silence (defensive; PATTERNS membership already checked).
        return block

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _impulse_train(
        self,
        t: np.ndarray,
        period: float,
        offset: float = 0.0,
        decay: float = 0.1,
        freq: float = 100.0,
        noise_blend: float = 0.0,
    ) -> np.ndarray:
        """Decaying-sine pulse train at `period` seconds; optional noise mix."""
        phase = (t - offset) % period
        env = np.exp(-phase / decay).astype(np.float32)
        sine = np.sin(2 * np.pi * freq * phase).astype(np.float32)
        if noise_blend > 0:
            noise = self._rng.standard_normal(t.shape[0]).astype(np.float32)
            body = (1 - noise_blend) * sine + noise_blend * noise
        else:
            body = sine
        return (0.5 * env * body).astype(np.float32)
