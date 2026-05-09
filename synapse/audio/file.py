"""Multi-channel WAV/FLAC playback as an AudioSource.

Stub for V1. Full implementation lands in phase 1.5 alongside the device
source. Useful for: reproducible visual output, demo videos, regression
tests where deterministic audio matters.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np


class FileSource:
    """Loop a multi-channel audio file as a real-time-paced source.

    Args:
        path: WAV / FLAC / etc. (anything libsndfile reads).
        loop: restart from the beginning when the end is reached. Default True.
    """

    n_channels: int = 14  # populated from the file at open()
    sample_rate: int
    block_size: int

    def __init__(self, path: str, loop: bool = True, block_size: int = 512) -> None:
        self.path = path
        self.loop = loop
        self.block_size = block_size
        self.sample_rate = 48_000  # filled in at open()

    def open(self) -> None:
        raise NotImplementedError(
            "FileSource is a phase-1.5 stub. Use MockSource for now: "
            "--source mock or --source mock:drums"
        )

    def close(self) -> None:
        pass

    def frames(self) -> Iterator[np.ndarray]:
        raise NotImplementedError("FileSource is a phase-1.5 stub.")
