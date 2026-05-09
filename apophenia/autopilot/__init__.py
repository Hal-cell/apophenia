"""Self-evolution engine. The autopilot replaces the V1 human-control
surface (web UI / sliders / presets) with a deterministic generator
that drives the shader state from `(wallclock_time, audio_features)`
alone.

Two pieces:
  * `wanderer.Wanderer` — a single 1D smooth-noise trajectory in
    [-1, 1], parametrised by seed + base period. Different seeds
    decorrelate, different periods give different timescales.
  * `modulator.Modulator` — a bank of Wanderers wired to a
    `VisualState`, with audio features feeding additive
    modulation on top. Reads each frame.
"""

from apophenia.autopilot.modulator import Modulator
from apophenia.autopilot.wanderer import Wanderer

__all__ = ["Modulator", "Wanderer"]
