"""Core Audio device source — real implementation.

Wraps any class-compliant input device via `sounddevice` (PortAudio under
the hood). Same code path serves:
  * Expert Sleepers ES-9 (the V1 production target)
  * BlackHole 16ch (DAW route-through, free)
  * Pro Tools Audio Bridge 16ch / 32ch / 64ch (Avid's equivalent)
  * Any other multi-channel USB / Thunderbolt interface

User selects a device by exact name; `apophenia devices` lists what's
available. We open a non-callback `InputStream` so reads block on the
device's natural cadence — there's no need to pace ourselves the way
`MockSource` does.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Iterator
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class DeviceSourceError(RuntimeError):
    """Raised on device-open / configuration failures.

    Distinct from `sounddevice.PortAudioError` so callers can catch a
    project-specific exception class without depending on PortAudio types.
    """


class DeviceSource:
    """Read live multi-channel audio from a Core Audio device.

    Args:
        device_name: exact device name as reported by Core Audio. Use
            `apophenia devices` to list what's available. Substring
            matches and case-insensitive matches are NOT performed —
            the user picks the exact string.
        n_channels: how many input channels to capture (default 14).
            Must be ≤ the device's `max_input_channels`.
        sample_rate: requested SR (default 48000). If the device doesn't
            support it, falls back to the device default with a warning.
        block_size: samples per `stream.read()` call (default 512).
            ~10.7ms at 48kHz; tuned for low-but-comfortable feature
            extraction latency.
    """

    n_channels: int
    sample_rate: int
    block_size: int

    def __init__(
        self,
        device_name: str,
        n_channels: int = 14,
        sample_rate: int = 48_000,
        block_size: int = 512,
    ) -> None:
        self.device_name = device_name
        self.n_channels = n_channels
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._stream: Any | None = None
        self._device_index: int | None = None
        self._stop = False

    # ------------------------------------------------------------------ #
    # AudioSource Protocol surface
    # ------------------------------------------------------------------ #

    def open(self) -> None:
        sd = _import_sounddevice()
        self._device_index = _resolve_device_name(sd, self.device_name)
        device_info = sd.query_devices(self._device_index)
        max_ch = int(device_info["max_input_channels"])

        if self.n_channels > max_ch:
            raise DeviceSourceError(
                f"requested {self.n_channels} channels but device "
                f"{self.device_name!r} only exposes {max_ch} input channels"
            )

        # Validate sample rate; fall back to device default if needed.
        self.sample_rate = _negotiate_sample_rate(
            sd,
            self._device_index,
            self.n_channels,
            self.sample_rate,
            int(device_info["default_samplerate"]),
        )

        self._stream = sd.InputStream(
            device=self._device_index,
            channels=self.n_channels,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
        )
        self._stream.start()
        self._stop = False
        logger.info(
            "DeviceSource opened: %r (idx=%d, %dch, %dHz, block=%d)",
            self.device_name,
            self._device_index,
            self.n_channels,
            self.sample_rate,
            self.block_size,
        )

    def close(self) -> None:
        self._stop = True
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                logger.exception("error closing device stream")
            self._stream = None

    def frames(self) -> Iterator[np.ndarray]:
        if self._stream is None:
            self.open()
        assert self._stream is not None
        while not self._stop:
            try:
                data, overflowed = self._stream.read(self.block_size)
            except Exception as e:  # noqa: BLE001 — propagate after logging
                logger.error("device read failed: %s", e)
                raise
            if overflowed:
                # Buffer overflow = consumer slower than device. Logged
                # but we keep going; downstream can detect via timestamps
                # if it cares.
                logger.warning("audio input buffer overflowed")
            # sounddevice gives shape (frames, channels); pipeline wants
            # (channels, frames). Use ascontiguousarray to materialise the
            # transposed memory layout — downstream numpy ops expect
            # C-contiguous arrays.
            yield np.ascontiguousarray(data.T)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _import_sounddevice() -> Any:
    """Lazy-import sounddevice so import-time failures (e.g. missing
    PortAudio on a CI host) are converted to actionable runtime errors.
    """
    try:
        import sounddevice as sd  # type: ignore[import-untyped]
    except ImportError as e:
        raise DeviceSourceError(
            "sounddevice is not installed; install it with `uv sync`"
        ) from e
    except OSError as e:
        # PortAudio dynamic library missing (Linux without libportaudio2,
        # or rare macOS install bug).
        raise DeviceSourceError(
            f"sounddevice failed to load PortAudio: {e}. "
            "On macOS this usually means `brew reinstall portaudio` is needed."
        ) from e
    return sd


def _resolve_device_name(sd: Any, name: str) -> int:
    """Find the (input-capable) device index matching `name` exactly.

    Multiple matches → pick the lowest index, log a warning. Core Audio
    occasionally exposes duplicates when an aggregate device contains a
    physical device of the same name; the lowest index is usually the
    physical one which is what users want.
    """
    devices = sd.query_devices()
    matches = [
        i
        for i, d in enumerate(devices)
        if d["name"] == name and d["max_input_channels"] > 0
    ]
    if not matches:
        available = [d["name"] for d in devices if d["max_input_channels"] > 0]
        raise DeviceSourceError(
            f"input device {name!r} not found. "
            f"available input devices: {available}"
        )
    if len(matches) > 1:
        logger.warning(
            "multiple input devices match %r (indices %s); using %d",
            name,
            matches,
            matches[0],
        )
    return matches[0]


def _negotiate_sample_rate(
    sd: Any,
    device_index: int,
    n_channels: int,
    requested: int,
    device_default: int,
) -> int:
    """Try `requested` SR first; if the device rejects it, fall back to
    the device's default SR and warn. Raises DeviceSourceError if neither
    works.
    """
    try:
        sd.check_input_settings(
            device=device_index,
            channels=n_channels,
            samplerate=requested,
            dtype="float32",
        )
        return requested
    except Exception:  # noqa: BLE001 — sd.PortAudioError, but we don't import it
        pass

    warnings.warn(
        f"device doesn't support {requested}Hz with {n_channels}ch; "
        f"falling back to device default {device_default}Hz",
        stacklevel=3,
    )
    try:
        sd.check_input_settings(
            device=device_index,
            channels=n_channels,
            samplerate=device_default,
            dtype="float32",
        )
        return device_default
    except Exception as e:  # noqa: BLE001
        raise DeviceSourceError(
            f"device cannot open {n_channels}ch at either {requested}Hz "
            f"or {device_default}Hz: {e}"
        ) from e


# --------------------------------------------------------------------------- #
# CLI helper: list available devices
# --------------------------------------------------------------------------- #


def list_devices() -> list[dict]:
    """Return input-capable devices with their key metadata.

    Each dict: {index, name, max_input_channels, default_samplerate}.
    """
    try:
        sd = _import_sounddevice()
    except DeviceSourceError:
        return []
    out: list[dict] = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0:
            continue
        out.append(
            {
                "index": i,
                "name": d["name"],
                "max_input_channels": int(d["max_input_channels"]),
                "default_samplerate": int(d["default_samplerate"]),
            }
        )
    return out
