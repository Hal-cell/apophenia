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
