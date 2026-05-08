"""Natural-language → shader-parameter interpreter.

Phase-10 replaces the V1 SDXL-Turbo image generator with a much smaller
component: a keyword-based mapper that turns prompts like
"slow warm bloom" into partial `VisualState` diffs. The diff is
deep-merged into the StateBus by the `/api/prompt` endpoint.

The keyword approach is deliberately simple — fixed vocabulary, no
model, instant + deterministic. A future phase will optionally bolt on
a local-LLM (Ollama) backend behind the same `PromptInterpreter`
interface for richer interpretations.
"""

from apophenia.prompt.interpreter import PromptInterpreter

__all__ = ["PromptInterpreter"]
