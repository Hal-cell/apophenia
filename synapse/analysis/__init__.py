"""Per-block extractors that consume the audio capture buffer and
produce semantically-meaningful per-channel signals.

  * `cv.CVDetector`         — slow DC value + rate of change per CV channel
  * `gate.GateDetector`     — Schmitt-triggered binary state + edge events
                              per gate channel
  * `spectrum.SpectrumDetector` — log-spaced 32-bin magnitude spectrum
                              per audio channel, throttled to ~30Hz
"""

from synapse.analysis.cv import CVDetector, CVFeatures
from synapse.analysis.gate import GateDetector, GateFeatures
from synapse.analysis.spectrum import SpectrumDetector, SpectrumFeatures

__all__ = [
    "CVDetector",
    "CVFeatures",
    "GateDetector",
    "GateFeatures",
    "SpectrumDetector",
    "SpectrumFeatures",
]
