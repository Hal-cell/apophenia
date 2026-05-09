"""AudioSource: pluggable input for the rest of the pipeline.

Three implementations, one Protocol. CLI flag `--source <spec>` picks one
via `parse_source_arg()`. See the vault spec `conduit/spec/audio-sources.md`
for full design rationale.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class AudioSource(Protocol):
    """An audio input source yielding multi-channel float32 blocks at real-time pace.

    Implementations must:
      * Yield `(n_channels, block_size)` arrays in [-1, 1].
      * Pace iteration to real-time (sleep between yields if generated faster).
        This keeps onset windows / CLAP framing identical across mock vs
        device sources.
      * Be safe to call `close()` from another thread.
    """

    n_channels: int
    sample_rate: int
    block_size: int

    def open(self) -> None: ...
    def close(self) -> None: ...

    def frames(self) -> Iterator[np.ndarray]:
        """Iterate blocks. Caller treats this as a real-time generator."""
        ...


# --------------------------------------------------------------------------- #
# CLI source-spec parser
# --------------------------------------------------------------------------- #

class SourceSpecError(ValueError):
    """Raised when a `--source` argument can't be parsed."""


def parse_source_arg(arg: str) -> AudioSource:
    """Resolve a `--source` CLI flag string into an `AudioSource` instance.

    Accepted forms:
      * `mock`                  → MockSource(pattern='silence')
      * `mock:<pattern>`         → MockSource(pattern)
      * `file:<path>`            → FileSource(path)
      * `device:<name>`          → DeviceSource(name)
      * `device:"<name with spaces>"` (caller usually unquotes; we accept either)

    The pattern / device-name parsing is permissive: anything after the first
    colon is the value, including extra colons, so `device:My:Audio:Box`
    works. We don't try to validate device existence here — DeviceSource
    raises at `open()` if the name doesn't match.
    """
    if not arg or ":" not in arg:
        kind, value = arg or "mock", ""
    else:
        kind, value = arg.split(":", 1)

    kind = kind.strip().lower()
    value = value.strip().strip('"').strip("'")

    if kind == "mock":
        # Lazy import so we don't pull in numpy synthesis until needed.
        from conduit.audio.mock import MockSource
        return MockSource(pattern=value or "silence")

    if kind == "file":
        if not value:
            raise SourceSpecError("file source requires a path: --source file:<path>")
        from conduit.audio.file import FileSource
        return FileSource(path=value)

    if kind == "device":
        if not value:
            raise SourceSpecError("device source requires a name: --source device:<name>")
        from conduit.audio.device import DeviceSource
        return DeviceSource(device_name=value)

    raise SourceSpecError(
        f"unknown source kind: {kind!r}. expected one of: mock, file, device"
    )
