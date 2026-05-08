"""Keyword-based prompt → state-diff interpreter.

Vocabulary is a flat dict of `keyword → partial state diff`. When
interpreting a prompt, we tokenise on whitespace, strip light
punctuation, look each token up, and deep-merge any matches into a
single output dict. Unknown tokens are silently ignored — this lets
performers write free-form text where most words are descriptive
filler and the system picks up the load-bearing ones.

Example:
    >>> PromptInterpreter().interpret("slow warm bloom")
    {
        "matched": ["slow", "warm", "bloom"],
        "partial": {
            "motion": {"speed": 0.4, "density": 0.6, "onset_sensitivity": 1.4},
            "palette": {"hue": 0.05, "saturation": 1.2},
            "mood": {"valence": 0.7},
        },
    }

When two matched keywords write to the same path, later tokens win
(the merge is left-to-right). This makes "slow fast" resolve to fast,
which is the intuitive read of natural language.

Synonyms map to the same diff (e.g. `purple == violet`). Vocabulary
covers four axes the user identified as the relevant control surface
for V1.5: motion (speed / density / sensitivity), brightness energy
(saturation / mood arousal), colour (palette hue + warmth), and
overall energy trajectory (channel weights, FX intensity).
"""

from __future__ import annotations

from typing import Any


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `update` into a copy of `base`. Lists / scalars
    in `update` replace; dicts merge field-wise. Same semantics as the
    StateBus deep-merge so the partials we produce flow cleanly through
    `state_bus.update(partial)`."""
    out = dict(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #
#
# Each entry is `keyword: partial-state-dict`. The partial gets deep-merged
# into the running diff for every matched token. All values must validate
# against `VisualState` — we test this exhaustively in test_prompt_interpreter.

VOCABULARY: dict[str, dict[str, Any]] = {
    # ---- Motion: speed ---- #
    "slow":      {"motion": {"speed": 0.4}},
    "calm":      {"motion": {"speed": 0.5}, "mood": {"arousal": -0.5}},
    "lazy":      {"motion": {"speed": 0.3}},
    "drifting":  {"motion": {"speed": 0.4, "density": 0.4}},
    "fast":      {"motion": {"speed": 1.6}},
    "rapid":     {"motion": {"speed": 1.7}},
    "agitated":  {"motion": {"speed": 1.5}, "mood": {"arousal": 0.7}},
    "violent":   {"motion": {"speed": 1.8, "onset_sensitivity": 1.7},
                  "mood": {"arousal": 0.9}},
    "frantic":   {"motion": {"speed": 1.9, "onset_sensitivity": 1.6}},
    "static":    {"motion": {"speed": 0.05}},
    "frozen":    {"motion": {"speed": 0.0}},

    # ---- Motion: density / texture ---- #
    "sparse":    {"motion": {"density": 0.15}},
    "thin":      {"motion": {"density": 0.2}},
    "dense":     {"motion": {"density": 0.85}},
    "thick":     {"motion": {"density": 0.8}},
    "fine":      {"motion": {"density": 0.75}},
    "chunky":    {"motion": {"density": 0.25}},
    "coarse":    {"motion": {"density": 0.3}},
    "grainy":    {"motion": {"density": 0.7}},

    # ---- Motion: sensitivity (onset response) ---- #
    "punchy":    {"motion": {"onset_sensitivity": 1.6}},
    "responsive":{"motion": {"onset_sensitivity": 1.4}},
    "soft":      {"motion": {"onset_sensitivity": 0.4}},
    "muted":     {"motion": {"onset_sensitivity": 0.3},
                  "palette": {"saturation": 0.5}},

    # ---- Energy / brightness ---- #
    "bright":    {"palette": {"saturation": 1.4},
                  "motion": {"density": 0.6}},
    "dim":       {"palette": {"saturation": 0.5}},
    "intense":   {"palette": {"saturation": 1.5},
                  "motion": {"onset_sensitivity": 1.4}},
    "subtle":    {"palette": {"saturation": 0.65},
                  "motion": {"speed": 0.6, "onset_sensitivity": 0.6}},

    # ---- Warmth (palette + mood) ---- #
    "warm":      {"palette": {"hue": 0.05, "saturation": 1.2},
                  "mood": {"valence": 0.7}},
    "hot":       {"palette": {"hue": 0.02, "saturation": 1.4},
                  "mood": {"valence": 0.9}},
    "cool":      {"palette": {"hue": 0.55, "saturation": 1.0},
                  "mood": {"valence": -0.5}},
    "cold":      {"palette": {"hue": 0.6, "saturation": 0.7},
                  "mood": {"valence": -0.8}},
    "icy":       {"palette": {"hue": 0.55, "saturation": 0.6},
                  "mood": {"valence": -0.9}},

    # ---- Specific colours (just shifts hue, leaves sat alone) ---- #
    "red":       {"palette": {"hue": 0.0}},
    "orange":    {"palette": {"hue": 0.07}},
    "yellow":    {"palette": {"hue": 0.15}},
    "green":     {"palette": {"hue": 0.33}},
    "cyan":      {"palette": {"hue": 0.5}},
    "blue":      {"palette": {"hue": 0.6}},
    "violet":    {"palette": {"hue": 0.78}},
    "purple":    {"palette": {"hue": 0.78}},
    "magenta":   {"palette": {"hue": 0.85}},
    "pink":      {"palette": {"hue": 0.9}},

    # ---- FX modifiers ---- #
    "smooth":    {"fx": {"glitch": 0.0, "chromatic": 0.0}},
    "clean":     {"fx": {"glitch": 0.0, "chromatic": 0.0}},
    "glitchy":   {"fx": {"glitch": 0.6}},
    "broken":    {"fx": {"glitch": 0.8, "chromatic": 0.4}},
    "shattered": {"fx": {"glitch": 0.5, "chromatic": 0.3},
                  "motion": {"onset_sensitivity": 1.7}},
    "lofi":      {"fx": {"chromatic": 0.5},
                  "palette": {"saturation": 0.7}},
    "neon":      {"fx": {"chromatic": 0.3},
                  "palette": {"saturation": 1.6}},
    "kaleido":   {"fx": {"kaleidoscope": 6}},
    "kaleidoscope": {"fx": {"kaleidoscope": 6}},
    "mirror":    {"fx": {"kaleidoscope": 2}},
    "fragmented":{"fx": {"kaleidoscope": 4}},

    # ---- Behaviour primitives ---- #
    "bloom":     {"motion": {"speed": 0.7, "density": 0.6,
                             "onset_sensitivity": 1.4}},
    "pulse":     {"motion": {"onset_sensitivity": 1.6}},
    "throb":     {"motion": {"onset_sensitivity": 1.5, "speed": 0.7}},
    "ripple":    {"motion": {"speed": 0.8, "density": 0.5}},
    "drift":     {"motion": {"speed": 0.5, "density": 0.4}},
    "flow":      {"motion": {"speed": 0.7, "density": 0.45}},
    "shatter":   {"fx": {"glitch": 0.5},
                  "motion": {"onset_sensitivity": 1.7}},
    "swarm":     {"motion": {"density": 0.85, "speed": 1.2}},
    "scatter":   {"motion": {"density": 0.3, "onset_sensitivity": 1.4}},
}


class PromptInterpreter:
    """Translates a free-form prompt into a partial `VisualState` dict.

    Stateless — `interpret()` is a pure function of the input string and
    the (immutable) `VOCABULARY` dict. Extending the vocabulary is a
    one-line edit; future LLM backends can subclass this to override
    `interpret()` while keeping the same return shape.
    """

    PUNCTUATION = ".,!?;:\"'()[]{}"

    def __init__(self, vocabulary: dict[str, dict[str, Any]] | None = None) -> None:
        self.vocabulary = vocabulary if vocabulary is not None else VOCABULARY

    def interpret(self, text: str) -> dict[str, Any]:
        """Parse `text` and return `{matched: [...], partial: {...}}`.

        `partial` is suitable for `state_bus.update()` directly. `matched`
        is the list of keywords (in order seen) that contributed to the
        diff — useful UI feedback so the performer can tell which words
        landed.
        """
        partial: dict[str, Any] = {}
        matched: list[str] = []
        for raw in text.lower().split():
            tok = raw.strip(self.PUNCTUATION)
            if not tok:
                continue
            entry = self.vocabulary.get(tok)
            if entry is None:
                continue
            partial = _deep_merge(partial, entry)
            matched.append(tok)
        return {"matched": matched, "partial": partial}
