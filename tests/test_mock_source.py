"""Smoke tests for MockSource and the source-spec parser.

These tests are deliberately small but exercise the contract:
  * `parse_source_arg` resolves CLI flags.
  * `MockSource` yields correctly-shaped blocks for every named pattern.
  * Patterns that should produce signal actually do (RMS > 0).
  * Real-time pacing isn't broken (yield rate ≈ block period).
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from synapse.audio.mock import N_CHANNELS, PATTERNS, MockSource
from synapse.audio.source import SourceSpecError, parse_source_arg


@pytest.mark.parametrize("pattern", PATTERNS)
def test_mock_block_shape(pattern: str) -> None:
    src = MockSource(pattern=pattern, block_size=128)
    src.open()
    try:
        gen = src.frames()
        block = next(gen)
        assert block.shape == (N_CHANNELS, 128)
        assert block.dtype == np.float32
        # No clipping or NaN slip-through.
        assert np.all(np.isfinite(block))
        assert np.all(np.abs(block) <= 1.5), "samples should stay near [-1, 1]"
    finally:
        src.close()


def test_silence_is_silent() -> None:
    src = MockSource(pattern="silence", block_size=128)
    src.open()
    try:
        block = next(src.frames())
        assert np.all(block == 0.0)
    finally:
        src.close()


@pytest.mark.parametrize("pattern", ["sines", "drums", "melody", "chaos", "single"])
def test_signal_patterns_produce_signal(pattern: str) -> None:
    """Non-silent patterns should output non-zero RMS within a few blocks.

    melody / chaos / single take more blocks than sines / drums (sparse onsets).
    Pull 50 blocks (~0.13 s at 48k/128) to be sure.
    """
    src = MockSource(pattern=pattern, block_size=128)
    src.open()
    try:
        rms_total = 0.0
        for i, block in enumerate(src.frames()):
            rms_total += float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
            if i >= 50:
                break
        assert rms_total > 0.0, f"pattern {pattern!r} produced silence"
    finally:
        src.close()


def test_unknown_pattern_falls_back_to_silence_with_warning() -> None:
    src = MockSource(pattern="not-a-real-pattern", block_size=64)
    with pytest.warns(UserWarning, match="unknown mock pattern"):
        src.open()
    try:
        block = next(src.frames())
        assert np.all(block == 0.0)
    finally:
        src.close()


def test_realtime_pacing_roughly_holds() -> None:
    """Pulling N blocks should take ~ N × block_period seconds.

    Tolerance is loose because we don't want to be flaky on CI. Just
    confirm we're not yielding faster than real-time (which would break
    onset windows downstream).
    """
    block_size = 256
    sample_rate = 48_000
    src = MockSource(pattern="sines", block_size=block_size, sample_rate=sample_rate)
    src.open()
    try:
        n_blocks = 10
        expected = n_blocks * block_size / sample_rate
        t0 = time.monotonic()
        for i, _ in enumerate(src.frames()):
            if i + 1 >= n_blocks:
                break
        elapsed = time.monotonic() - t0
        # Should be at least 80% of expected; we sleep to pace.
        assert elapsed >= expected * 0.8, (
            f"yielded {elapsed:.4f}s for {n_blocks} blocks "
            f"of {block_size}/{sample_rate}s (expected ~{expected:.4f}s)"
        )
    finally:
        src.close()


# --------------------------------------------------------------------------- #
# parse_source_arg
# --------------------------------------------------------------------------- #


def test_parse_source_default_returns_mock() -> None:
    src = parse_source_arg("mock")
    assert isinstance(src, MockSource)
    assert src.pattern == "silence"


def test_parse_source_with_pattern() -> None:
    src = parse_source_arg("mock:drums")
    assert isinstance(src, MockSource)
    assert src.pattern == "drums"


def test_parse_source_unknown_kind_raises() -> None:
    with pytest.raises(SourceSpecError):
        parse_source_arg("zoo:thing")


def test_parse_source_file_requires_path() -> None:
    with pytest.raises(SourceSpecError):
        parse_source_arg("file:")


def test_parse_source_device_requires_name() -> None:
    with pytest.raises(SourceSpecError):
        parse_source_arg("device:")
