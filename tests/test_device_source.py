"""Tests for `DeviceSource` — the wrapper around sounddevice / Core Audio.

We mock the entire sounddevice module so tests don't require a real
audio device. The mock exposes:
  * `query_devices()` returning a controllable device list
  * `check_input_settings()` raising on unsupported configs
  * `InputStream` returning a mock stream with `read()` yielding fake data

Tests focus on DeviceSource's logic — name resolution, sample-rate
negotiation, channel-count validation, error reporting — not on
sounddevice or PortAudio internals.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from synapse.audio import device as device_mod
from synapse.audio.device import (
    DeviceSource,
    DeviceSourceError,
    _negotiate_sample_rate,
    _resolve_device_name,
    list_devices,
)

# --------------------------------------------------------------------------- #
# Mock sounddevice fixture
# --------------------------------------------------------------------------- #


def _fake_sd(devices: list[dict], rate_supported: set[tuple[int, int]] | None = None) -> Any:
    """Build a MagicMock that quacks like the sounddevice module.

    Args:
        devices: list of device-info dicts. Each must have `name` and
                 `max_input_channels` and `default_samplerate`.
        rate_supported: set of (device_index, samplerate) pairs that
                 `check_input_settings` accepts. Anything else raises.
                 None → all rates supported.
    """
    sd = MagicMock(name="sounddevice")
    # Set PortAudioError to a real exception class so `except` works in
    # production code paths that catch it.
    sd.PortAudioError = type("PortAudioError", (Exception,), {})

    def query_devices(idx: int | None = None) -> Any:
        if idx is None:
            return devices
        return devices[idx]

    sd.query_devices.side_effect = query_devices

    def check_input_settings(
        device: int, channels: int, samplerate: int, dtype: str
    ) -> None:
        if rate_supported is not None and (device, samplerate) not in rate_supported:
            raise sd.PortAudioError(f"unsupported rate {samplerate} for device {device}")
        if channels > devices[device]["max_input_channels"]:
            raise sd.PortAudioError(f"too many channels: {channels}")

    sd.check_input_settings.side_effect = check_input_settings

    # InputStream mock — any subsequent `.read(N)` returns silence of the
    # right shape and `overflowed=False`. `.start()` / `.stop()` /
    # `.close()` are no-ops on the MagicMock.
    def make_input_stream(
        device: int, channels: int, samplerate: int, blocksize: int, dtype: str
    ) -> Any:
        stream = MagicMock(name=f"InputStream<dev={device}>")
        stream.read.side_effect = lambda n: (
            np.zeros((n, channels), dtype=np.float32),
            False,
        )
        return stream

    sd.InputStream.side_effect = make_input_stream
    return sd


@pytest.fixture
def fake_two_devices(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Two-device system: an ES-9 (14ch) and a Pro Tools Bridge (16ch)."""
    sd = _fake_sd(
        [
            {"name": "MacBook Pro Microphone", "max_input_channels": 1, "default_samplerate": 48000},
            {"name": "ES-9", "max_input_channels": 14, "default_samplerate": 48000},
            {"name": "Pro Tools Audio Bridge 16ch", "max_input_channels": 16, "default_samplerate": 48000},
        ],
    )
    # Patch the lazy-importer so `_import_sounddevice()` returns our mock.
    monkeypatch.setattr(device_mod, "_import_sounddevice", lambda: sd)
    return sd


@pytest.fixture
def fake_44100_only(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Single device that only accepts 44100Hz, default samplerate 44100."""
    sd = _fake_sd(
        [{"name": "Cheap USB Mic", "max_input_channels": 14, "default_samplerate": 44100}],
        rate_supported={(0, 44100)},
    )
    monkeypatch.setattr(device_mod, "_import_sounddevice", lambda: sd)
    return sd


# --------------------------------------------------------------------------- #
# _resolve_device_name
# --------------------------------------------------------------------------- #


def test_resolve_finds_named_device(fake_two_devices: Any) -> None:
    idx = _resolve_device_name(fake_two_devices, "ES-9")
    assert idx == 1


def test_resolve_finds_pro_tools_bridge(fake_two_devices: Any) -> None:
    idx = _resolve_device_name(fake_two_devices, "Pro Tools Audio Bridge 16ch")
    assert idx == 2


def test_resolve_missing_raises(fake_two_devices: Any) -> None:
    with pytest.raises(DeviceSourceError) as exc:
        _resolve_device_name(fake_two_devices, "Nonexistent")
    assert "Nonexistent" in str(exc.value)
    # Error message should list available devices to help the user.
    assert "ES-9" in str(exc.value)
    assert "Pro Tools Audio Bridge 16ch" in str(exc.value)


def test_resolve_skips_output_only_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    sd = _fake_sd(
        [
            {"name": "Output Speaker", "max_input_channels": 0, "default_samplerate": 48000},
            {"name": "Output Speaker", "max_input_channels": 14, "default_samplerate": 48000},
        ],
    )
    monkeypatch.setattr(device_mod, "_import_sounddevice", lambda: sd)
    # Exact-match name shared between an output-only and an input device:
    # we should pick the input one.
    idx = _resolve_device_name(sd, "Output Speaker")
    assert idx == 1


# --------------------------------------------------------------------------- #
# _negotiate_sample_rate
# --------------------------------------------------------------------------- #


def test_sample_rate_accepts_default(fake_two_devices: Any) -> None:
    sr = _negotiate_sample_rate(fake_two_devices, 1, 14, 48000, 48000)
    assert sr == 48000


def test_sample_rate_falls_back_with_warning(fake_44100_only: Any) -> None:
    with pytest.warns(UserWarning, match="44100Hz"):
        sr = _negotiate_sample_rate(fake_44100_only, 0, 14, 48000, 44100)
    assert sr == 44100


def test_sample_rate_no_valid_rate_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    sd = _fake_sd(
        [{"name": "Bad Device", "max_input_channels": 14, "default_samplerate": 22050}],
        rate_supported=set(),  # nothing supported
    )
    monkeypatch.setattr(device_mod, "_import_sounddevice", lambda: sd)
    with pytest.warns(UserWarning), pytest.raises(DeviceSourceError):
        _negotiate_sample_rate(sd, 0, 14, 48000, 22050)


# --------------------------------------------------------------------------- #
# DeviceSource end-to-end (with mock sd)
# --------------------------------------------------------------------------- #


def test_device_source_open_and_read(fake_two_devices: Any) -> None:
    src = DeviceSource("ES-9", n_channels=14, block_size=128)
    src.open()
    try:
        gen = src.frames()
        block = next(gen)
        assert block.shape == (14, 128)
        assert block.dtype == np.float32
    finally:
        src.close()
    # After close, stream should be torn down.
    assert src._stream is None


def test_device_source_too_many_channels_raises(fake_two_devices: Any) -> None:
    # ES-9 has 14ch; asking for 16 should fail at open().
    src = DeviceSource("ES-9", n_channels=16)
    with pytest.raises(DeviceSourceError, match="14 input channels"):
        src.open()


def test_device_source_unknown_device_raises(fake_two_devices: Any) -> None:
    src = DeviceSource("Imaginary Audio Box")
    with pytest.raises(DeviceSourceError, match="Imaginary Audio Box"):
        src.open()


def test_device_source_falls_back_sample_rate(fake_44100_only: Any) -> None:
    src = DeviceSource("Cheap USB Mic", n_channels=14)
    with pytest.warns(UserWarning, match="44100Hz"):
        src.open()
    try:
        assert src.sample_rate == 44100
    finally:
        src.close()


# --------------------------------------------------------------------------- #
# list_devices
# --------------------------------------------------------------------------- #


def test_list_devices_filters_to_input_capable(monkeypatch: pytest.MonkeyPatch) -> None:
    sd = _fake_sd(
        [
            {"name": "Speaker (output-only)", "max_input_channels": 0, "default_samplerate": 48000},
            {"name": "ES-9", "max_input_channels": 14, "default_samplerate": 48000},
        ],
    )
    monkeypatch.setattr(device_mod, "_import_sounddevice", lambda: sd)
    devs = list_devices()
    assert len(devs) == 1
    assert devs[0]["name"] == "ES-9"
    assert devs[0]["max_input_channels"] == 14
    assert devs[0]["default_samplerate"] == 48000
    assert devs[0]["index"] == 1  # original index preserved


def test_list_devices_returns_empty_on_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> Any:
        raise DeviceSourceError("sounddevice unavailable")

    monkeypatch.setattr(device_mod, "_import_sounddevice", boom)
    assert list_devices() == []
