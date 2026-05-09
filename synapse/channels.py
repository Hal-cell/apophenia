"""Per-channel role configuration.

Each input channel of the audio source plays one of three roles:

  * `AUDIO` — full audio analysis (RMS / peak / centroid / onset
              envelope + FFT spectrum). For instrument signals,
              field recordings, anything bipolar / AC-flavoured.
  * `CV`    — slow DC value extraction. For Eurorack control voltage
              inputs (LFOs, envelopes, sequencer outs). Output is
              the smoothed channel value plus its rate of change.
  * `GATE`  — Schmitt-trigger-based binary state + rising/falling
              edge events. For Eurorack gates / triggers / clock.

A `ChannelMap` holds the role assignment for every input channel.
The default for unassigned channels is `AUDIO`.

CLI parsing accepts a flexible range syntax:

    --gate "1,2"          → channels 1, 2
    --cv   "3-6"          → channels 3, 4, 5, 6
    --audio "7-14"        → channels 7..14
    --cv   "1,3-5,8"      → channels 1, 3, 4, 5, 8

Channel numbers are 1-based on the CLI (matching how performers
think about jacks on the panel) and converted to 0-based internally.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from enum import StrEnum


class ChannelRole(StrEnum):
    """What kind of signal lives on a given channel.

    Inheriting from `str` makes the enum JSON-serialisable for the
    web meter payload + OSC sender's role broadcast — `ChannelRole.CV`
    serialises as the string `"cv"` directly.
    """

    AUDIO = "audio"
    CV = "cv"
    GATE = "gate"


class ChannelMap:
    """Holds the role assignment for every channel of an audio source.

    Construct via the `from_cli()` classmethod which parses three
    range strings (one each for gate / cv / audio) and validates
    that:
      * channel numbers are 1..n_channels
      * no channel is assigned to two different roles
      * unassigned channels default to AUDIO
    """

    def __init__(self, roles: list[ChannelRole]) -> None:
        if not roles:
            raise ValueError("ChannelMap requires at least one channel")
        self._roles = list(roles)

    def __len__(self) -> int:
        return len(self._roles)

    def role(self, channel_idx: int) -> ChannelRole:
        """Get the role for a 0-indexed channel."""
        return self._roles[channel_idx]

    def channels_with(self, role: ChannelRole) -> list[int]:
        """Return 0-indexed channel numbers that have the given role."""
        return [i for i, r in enumerate(self._roles) if r == role]

    def to_dict(self) -> dict[str, list[int]]:
        """JSON-serialisable summary for the web meter / OSC bootstrap."""
        return {
            role.value: self.channels_with(role)
            for role in ChannelRole
        }

    @classmethod
    def from_cli(
        cls,
        n_channels: int,
        gate: str | None = None,
        cv: str | None = None,
        audio: str | None = None,
    ) -> ChannelMap:
        """Build a ChannelMap from CLI range strings.

        Channels not mentioned in any of the three strings default to
        AUDIO. Channels mentioned in multiple strings raise ValueError.
        """
        if n_channels <= 0:
            raise ValueError(f"n_channels must be > 0, got {n_channels}")
        roles: list[ChannelRole] = [ChannelRole.AUDIO] * n_channels
        assigned: dict[int, ChannelRole] = {}

        for spec, role in (
            (gate, ChannelRole.GATE),
            (cv, ChannelRole.CV),
            (audio, ChannelRole.AUDIO),
        ):
            if not spec:
                continue
            for ch in _parse_range_spec(spec):
                if ch < 1 or ch > n_channels:
                    raise ValueError(
                        f"channel {ch} out of range [1, {n_channels}] (role {role.value})"
                    )
                idx = ch - 1
                if idx in assigned and assigned[idx] != role:
                    raise ValueError(
                        f"channel {ch} assigned both {assigned[idx].value} and {role.value}"
                    )
                assigned[idx] = role
                roles[idx] = role
        return cls(roles)


class ChannelRolesController:
    """Thread-safe live channel-role state.

    The audio thread reads roles every block (`get()` returns a snapshot
    list to avoid holding the lock while iterating); the FastAPI HTTP
    thread mutates them via `set_one()` or `set_all()` when the user
    clicks a role badge in the web UI.

    Validation:
      * `set_one` rejects out-of-range indices and unknown role strings
      * `set_all` rejects length mismatches against `n_channels`

    The audio loop snapshots once per block and uses that snapshot for
    the entire block's filtering — so a mid-block role change is
    visible at most one block later, never half-applied.
    """

    def __init__(self, roles: list[ChannelRole]) -> None:
        if not roles:
            raise ValueError("ChannelRolesController requires at least one channel")
        self._lock = threading.Lock()
        self._roles: list[ChannelRole] = list(roles)
        # Monotonic version counter — bumped on every successful update.
        # The web UI / WS payload exposes this so consumers can
        # cheap-detect "did the role list change since I last looked"
        # without comparing element-wise.
        self._version = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._roles)

    @property
    def n_channels(self) -> int:
        with self._lock:
            return len(self._roles)

    def get(self) -> list[ChannelRole]:
        """Return a snapshot copy of the current role list."""
        with self._lock:
            return list(self._roles)

    def role(self, channel_idx: int) -> ChannelRole:
        with self._lock:
            return self._roles[channel_idx]

    def channels_with(self, role: ChannelRole) -> list[int]:
        with self._lock:
            return [i for i, r in enumerate(self._roles) if r == role]

    def version(self) -> int:
        with self._lock:
            return self._version

    def set_one(self, channel_idx: int, role: ChannelRole | str) -> None:
        """Update one channel's role. Raises ValueError on bad input."""
        role_enum = _coerce_role(role)
        with self._lock:
            if not 0 <= channel_idx < len(self._roles):
                raise ValueError(
                    f"channel index {channel_idx} out of range "
                    f"[0, {len(self._roles)})"
                )
            self._roles[channel_idx] = role_enum
            self._version += 1

    def set_all(self, roles: list[ChannelRole | str]) -> None:
        """Replace the entire role list. Length must match n_channels."""
        coerced = [_coerce_role(r) for r in roles]
        with self._lock:
            if len(coerced) != len(self._roles):
                raise ValueError(
                    f"expected {len(self._roles)} roles, got {len(coerced)}"
                )
            self._roles = coerced
            self._version += 1

    def snapshot(self) -> ChannelMap:
        """Return an immutable ChannelMap snapshot (for to_dict() etc)."""
        with self._lock:
            return ChannelMap(list(self._roles))


def _coerce_role(value: ChannelRole | str) -> ChannelRole:
    """Accept a `ChannelRole` or a string and return a `ChannelRole`,
    raising ValueError on unknown strings."""
    if isinstance(value, ChannelRole):
        return value
    if isinstance(value, str):
        # Case-insensitive for ergonomics; canonical values are lowercase.
        try:
            return ChannelRole(value.lower())
        except ValueError as e:
            raise ValueError(
                f"unknown role {value!r}; expected one of "
                f"{[r.value for r in ChannelRole]}"
            ) from e
    raise ValueError(f"role must be ChannelRole or str, got {type(value).__name__}")


def _parse_range_spec(spec: str) -> Iterable[int]:
    """Parse `'1,3-5,8'` → `[1, 3, 4, 5, 8]`. Whitespace tolerated.

    Ranges are inclusive on both ends. Single integers are allowed.
    Empty / pure-whitespace input yields an empty result.
    """
    out: list[int] = []
    spec = spec.strip()
    if not spec:
        return out
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            try:
                lo = int(lo_s.strip())
                hi = int(hi_s.strip())
            except ValueError as e:
                raise ValueError(f"bad range {chunk!r}") from e
            if lo > hi:
                raise ValueError(f"empty range {chunk!r} (lo > hi)")
            out.extend(range(lo, hi + 1))
        else:
            try:
                out.append(int(chunk))
            except ValueError as e:
                raise ValueError(f"bad channel number {chunk!r}") from e
    return out
