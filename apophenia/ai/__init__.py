"""AI generation tier — SDXL-Turbo single-step diffusion driving the
compositor's "AI" channel.

Only the bus + loop are imported eagerly; the actual SDXL pipeline lives
behind a lazy load in `sdxl_turbo.SDXLTurboGenerator.load()` so installs
without the [ai] extra (no torch / diffusers) don't pay the import cost.
"""

from apophenia.ai.bus import AIBus, AIFrame
from apophenia.ai.loop import ai_loop

__all__ = ["AIBus", "AIFrame", "ai_loop"]
