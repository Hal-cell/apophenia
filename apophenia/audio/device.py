"""Core Audio device source — wraps any class-compliant interface.

Stub for V1. Full implementation lands in phase 1.5. Same code path will
serve real ES-9, BlackHole 16ch, or any other multi-channel USB interface.
Selection is by exact device-name match.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np


class DeviceSource:
    """Read live multi-channel audio from a Core Audio device.

    Args:
        device_name: exact string from the system's device list, e.g. "ES-9"
                     or "BlackHole 16ch". Use `apophenia devices` (CLI) to
                     list available names.
        n_channels: how many channels to capture from the device.
                    Default 14 (ES-9 / BlackHole 16ch capacity).
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

    def open(self) -> None:
        raise NotImplementedError(
            "DeviceSource is a phase-1.5 stub. Use MockSource for now: "
            "--source mock or --source mock:drums"
        )

    def close(self) -> None:
        pass

    def frames(self) -> Iterator[np.ndarray]:
        raise NotImplementedError("DeviceSource is a phase-1.5 stub.")


def list_devices() -> list[str]:
    """Return the names of available Core Audio input devices.

    Used by `apophenia devices` CLI subcommand.
    """
    try:
        import sounddevice as sd
    except ImportError:
        return []
    return [
        d["name"]
        for d in sd.query_devices()
        if d["max_input_channels"] > 0
    ]
