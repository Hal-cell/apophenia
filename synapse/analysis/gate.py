"""Gate (trigger) detection per channel.

A "gate" channel on a DC-coupled audio interface carries a binary-
ish signal — Eurorack standard is ~+5V high / 0V low, surfaced as
roughly +0.5..1.0 high / 0.0 low after the audio normalisation.
Gates can be sustained (envelope sustain pedal style) or
percussive (drum trigger style).

We use a **Schmitt trigger** (hysteresis comparator) so analog noise
near the threshold doesn't toggle the state repeatedly:

  * Going low → high: requires `peak ≥ HIGH_THRESHOLD` (default 0.5)
  * Going high → low: requires `peak ≤ LOW_THRESHOLD` (default 0.3)

The sample-block peak is the trigger, not the per-block mean —
gate edges within a block (e.g. a 2ms trigger pulse) might miss the
mean threshold if the pulse is short relative to the block.

For each gate channel the detector emits per block:
  * `state` — boolean, current high/low
  * `rising_edge`  — boolean, True only on the block where state went 0→1
  * `falling_edge` — boolean, True only on the block where state went 1→0

Edges are exposed as one-block transients so the OSC sender / Max
patch can treat them as "bang" events (e.g. drive an envelope, fire
a one-shot in Unreal). Per-channel thresholds can be overridden if
some gates are noisier than others.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GateFeatures:
    """Per-block gate state for the configured gate channels.

    All length-N where N = number of gate channels. `channel_indices`
    are 0-based source-channel indices (matches the audio block layout).
    """

    channel_indices: list[int]
    states: list[bool]
    rising_edges: list[bool]
    falling_edges: list[bool]
    block_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_channels": list(self.channel_indices),
            "gate_states": [bool(s) for s in self.states],
            "gate_rising": [bool(e) for e in self.rising_edges],
            "gate_falling": [bool(e) for e in self.falling_edges],
            "gate_block_count": self.block_count,
        }


class GateDetector:
    """Schmitt-triggered binary state per gate channel."""

    DEFAULT_HIGH = 0.5
    DEFAULT_LOW = 0.3

    def __init__(
        self,
        gate_channel_indices: list[int],
        high_threshold: float = DEFAULT_HIGH,
        low_threshold: float = DEFAULT_LOW,
    ) -> None:
        if high_threshold <= low_threshold:
            raise ValueError(
                "high_threshold must be > low_threshold "
                f"(got {high_threshold} ≤ {low_threshold})"
            )
        self.channel_indices = list(gate_channel_indices)
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        # Per-channel current state (False = low, True = high).
        self._states = np.zeros(len(self.channel_indices), dtype=bool)

    def process(self, block: np.ndarray, block_count: int = 0) -> GateFeatures:
        """Apply Schmitt trigger to each gate channel for this block.

        Uses the per-block *peak* (max abs value), not the mean — gates
        can be very brief pulses (a 2ms Eurorack trigger barely
        averages to 0.1 over a 10.6ms block, but its peak is well above
        threshold).
        """
        if not self.channel_indices:
            return GateFeatures(
                channel_indices=[], states=[], rising_edges=[], falling_edges=[],
                block_count=block_count,
            )
        peaks = np.array(
            [float(np.max(np.abs(block[ch]))) for ch in self.channel_indices],
            dtype=np.float64,
        )
        prev = self._states.copy()
        # State machine: stay where you are unless you cross the
        # appropriate threshold.
        new_state = self._states.copy()
        new_state[(~self._states) & (peaks >= self.high_threshold)] = True
        new_state[self._states & (peaks <= self.low_threshold)] = False
        self._states = new_state
        rising = (~prev) & new_state
        falling = prev & (~new_state)
        return GateFeatures(
            channel_indices=list(self.channel_indices),
            states=[bool(s) for s in new_state],
            rising_edges=[bool(e) for e in rising],
            falling_edges=[bool(e) for e in falling],
            block_count=block_count,
        )
