"""Per-block extractors that consume the audio capture buffer and
produce semantically-meaningful per-channel signals.

  * `cv.CVDetector`   — slow DC value + rate of change per CV channel
  * `gate.GateDetector` — Schmitt-triggered binary state + edge events
                          per gate channel
"""

from synapse.analysis.cv import CVDetector, CVFeatures
from synapse.analysis.gate import GateDetector, GateFeatures

__all__ = ["CVDetector", "CVFeatures", "GateDetector", "GateFeatures"]
