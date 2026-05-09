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
    # `dense` writes both motion.density and force.cohesion — phase-14
    # made these conceptually paired (more particles + held tighter).
    "dense":     {"motion": {"density": 0.85},
                  "force": {"cohesion": 0.75}},
    "thick":     {"motion": {"density": 0.8},
                  "force": {"cohesion": 0.7}},
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
    "smooth":    {"fx": {"glitch": 0.0, "chromatic": 0.0, "trail": 0.0}},
    "clean":     {"fx": {"glitch": 0.0, "chromatic": 0.0, "trail": 0.0}},
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

    # ---- Trail / feedback ---- #
    "trail":     {"fx": {"trail": 0.7}},
    # `trails` is defined later in the streak section — combines
    # screen-space feedback trail + per-particle velocity streak.
    "smear":     {"fx": {"trail": 0.85}},
    "ghost":     {"fx": {"trail": 0.8}, "palette": {"saturation": 0.7}},
    "ghosting":  {"fx": {"trail": 0.85}},
    "sustained": {"fx": {"trail": 0.6},
                  "motion": {"speed": 0.6, "onset_sensitivity": 0.7}},
    "echo":      {"fx": {"trail": 0.75}},
    "lingering": {"fx": {"trail": 0.65}},
    "decay":     {"fx": {"trail": 0.5}},  # mid-trail, "fading away"

    # ---- 3D camera (phase 12) ---- #
    # The 3D particle world has 14 emitters on a ring around the origin.
    # Camera vocabulary tunes how the user views that scene.
    "close":     {"camera": {"distance": 2.5}},
    "near":      {"camera": {"distance": 3.0}},
    "wide":      {"camera": {"distance": 8.0, "fov_deg": 80.0}},
    "far":       {"camera": {"distance": 12.0}},
    "intimate":  {"camera": {"distance": 2.5, "fov_deg": 50.0}},
    "epic":      {"camera": {"distance": 10.0, "fov_deg": 75.0}},
    "overhead":  {"camera": {"elevation": 70.0}},
    "level":     {"camera": {"elevation": 0.0}},
    "tilted":    {"camera": {"elevation": 35.0}},
    "underground": {"camera": {"elevation": -25.0}},
    # Orbit speed.
    "still":     {"camera": {"autorotate": False}},
    "orbiting":  {"camera": {"autorotate": True, "orbit_speed": 0.08}},
    "swirling":  {"camera": {"autorotate": True, "orbit_speed": 0.18},
                  "motion": {"speed": 1.2}},
    "vortex":    {"camera": {"autorotate": True, "orbit_speed": 0.25},
                  "motion": {"density": 0.85, "onset_sensitivity": 1.4}},
    "spiral":    {"camera": {"autorotate": True, "orbit_speed": 0.15}},
    "gentle":    {"camera": {"autorotate": True, "orbit_speed": 0.03},
                  "motion": {"speed": 0.6}},

    # ---- Audio-reactivity modifiers (phase 13) ---- #
    # These don't write camera params directly — they set `mood.arousal`,
    # which is what couples audio to the camera at runtime in the
    # particle engine (orbit_speed and elevation get modulated by
    # arousal × audio_intensity each frame).
    "reactive":   {"mood": {"arousal": 0.6}},
    "breathing":  {"mood": {"arousal": 0.3},
                   "motion": {"speed": 0.7, "onset_sensitivity": 0.8}},
    "pulsing":    {"mood": {"arousal": 0.7},
                   "motion": {"onset_sensitivity": 1.6}},
    "volatile":   {"mood": {"arousal": 0.9},
                   "motion": {"speed": 1.5, "onset_sensitivity": 1.7}},
    "anchored":   {"mood": {"arousal": -0.5},
                   "camera": {"autorotate": False}},

    # ---- Particle force / cluster shaping (phase 14) ---- #
    # These tune the four force levers — noise / vortex / cohesion /
    # max_speed — toward common aesthetic targets.
    "cluster":    {"force": {"cohesion": 0.85, "vortex": 0.5, "noise": 0.3}},
    "cohesive":   {"force": {"cohesion": 0.85, "vortex": 0.4}},
    "tight":      {"force": {"cohesion": 0.9, "max_speed": 1.4}},
    "fluid":      {"force": {"noise": 0.7, "vortex": 0.3, "cohesion": 0.55,
                             "max_speed": 1.8}},
    "flowing":    {"force": {"noise": 0.75, "vortex": 0.25, "cohesion": 0.5}},
    "liquid":     {"force": {"noise": 0.75, "vortex": 0.4, "cohesion": 0.6,
                             "max_speed": 1.6}},
    "chaotic":    {"force": {"noise": 0.95, "vortex": 0.7, "cohesion": 0.2,
                             "max_speed": 4.0},
                   "mood": {"arousal": 0.7}},
    "turbulent":  {"force": {"noise": 0.9, "vortex": 0.6, "cohesion": 0.3,
                             "max_speed": 3.5}},
    "stormy":     {"force": {"noise": 0.95, "vortex": 0.55, "max_speed": 4.0},
                   "mood": {"arousal": 0.8}},
    "tornado":    {"force": {"vortex": 0.95, "cohesion": 0.65, "noise": 0.4,
                             "max_speed": 3.0}},
    "whirlpool":  {"force": {"vortex": 0.9, "cohesion": 0.7, "noise": 0.3}},
    "cyclone":    {"force": {"vortex": 0.85, "cohesion": 0.6, "noise": 0.5,
                             "max_speed": 3.2}},
    # Aesthetic shorthand.
    "data":       {"force": {"cohesion": 0.7, "vortex": 0.2, "noise": 0.3,
                             "max_speed": 1.2},
                   "palette": {"saturation": 0.25},
                   "motion": {"density": 0.9}},
    "ikeda":      {"force": {"cohesion": 0.75, "vortex": 0.15, "noise": 0.25,
                             "max_speed": 1.0},
                   "palette": {"saturation": 0.15},
                   "motion": {"density": 0.95}},
    "digital":    {"force": {"cohesion": 0.7, "vortex": 0.3, "noise": 0.4},
                   "palette": {"saturation": 0.4}},
    "minimal":    {"force": {"cohesion": 0.65, "vortex": 0.2, "noise": 0.3},
                   "palette": {"saturation": 0.4}},
    # Anti-cluster: scattering / dispersion.
    "dispersed":  {"force": {"cohesion": 0.05, "vortex": 0.15, "noise": 0.7,
                             "max_speed": 4.0}},
    "scattered":  {"force": {"cohesion": 0.0, "noise": 0.6, "vortex": 0.2}},
    "exploding":  {"force": {"cohesion": 0.0, "vortex": 0.1, "noise": 0.4,
                             "max_speed": 5.0},
                   "motion": {"onset_sensitivity": 1.7}},

    # ---- Streak length (phase 16) ---- #
    # Each particle is rendered as a velocity-aligned line from
    # `pos - vel * streak_length` (tail) to `pos` (head). At 0 the
    # line is degenerate and you see a near-point; at high values
    # particles look like full flow ribbons.
    "streaks":    {"force": {"streak_length": 0.18}},
    "lines":      {"force": {"streak_length": 0.20}},
    "ribbons":    {"force": {"streak_length": 0.30}},
    # Combine screen-space feedback trail (fx.trail) with per-particle
    # velocity streak — gives the most "smeary motion" reading.
    "trails":     {"force": {"streak_length": 0.22},
                   "fx": {"trail": 0.7}},
    "comet":      {"force": {"streak_length": 0.40, "max_speed": 3.0}},
    "wisps":      {"force": {"streak_length": 0.25, "cohesion": 0.5,
                             "max_speed": 1.4}},
    # Anti: kill streaks → render as points.
    "points":     {"force": {"streak_length": 0.0}},
    "dots":       {"force": {"streak_length": 0.0}},
    "stippled":   {"force": {"streak_length": 0.0, "cohesion": 0.6}},

    # ---- Emitter pattern (phase 17) ---- #
    # Reshape where the 14 audio-channel anchors sit in 3D space.
    # Particles still cluster around their home anchor (cohesion), so
    # changing the pattern reshapes the entire scene's geometry.
    "ring":       {"emitter": {"pattern": "ring"}},
    "grid":       {"emitter": {"pattern": "grid"}},
    "linear":     {"emitter": {"pattern": "line"}},
    "horizon":    {"emitter": {"pattern": "line", "radius": 3.0},
                   "camera": {"elevation": 5.0}},
    "constellation": {"emitter": {"pattern": "sphere"}},
    "globe":      {"emitter": {"pattern": "sphere", "radius": 2.0}},
    "curve":      {"emitter": {"pattern": "lissajous"}},
    "knot":       {"emitter": {"pattern": "lissajous", "radius": 2.0}},

    # Drift modifiers — emitters wander on per-channel orbits.
    "wandering":  {"emitter": {"motion_amp": 0.6, "motion_speed": 0.4}},
    "restless":   {"emitter": {"motion_amp": 0.8, "motion_speed": 0.8}},
    "drifting_emitters": {"emitter": {"motion_amp": 0.4, "motion_speed": 0.3}},
    "static_emitters":   {"emitter": {"motion_amp": 0.0}},

    # Radius modifiers — uniform scale on the pattern.
    "expanding":  {"emitter": {"radius": 3.0}},
    "contracting": {"emitter": {"radius": 0.8}},
    "tight_pattern":  {"emitter": {"radius": 0.7}},
    "wide_pattern":   {"emitter": {"radius": 3.5}},

    # Phase-18 morph / dynamics modifiers. The pattern transition itself
    # is automatic on pattern change — these keywords either pre-tune
    # mood.arousal so emitters wobble more under audio, or push
    # motion_amp directly.
    "morphing":   {"emitter": {"motion_amp": 0.5, "motion_speed": 0.6},
                   "mood": {"arousal": 0.4}},
    "shifting":   {"emitter": {"motion_amp": 0.6, "motion_speed": 0.5}},
    "evolving":   {"emitter": {"motion_amp": 0.55, "motion_speed": 0.4},
                   "mood": {"arousal": 0.3}},
    # Phase-18: extend `drifting` (already defined under motion-speed)
    # so it ALSO triggers emitter wobble when used in a phrase like
    # "drifting constellation" — the existing definition's motion fields
    # combine with these emitter fields via the deep-merge.
    "slowfloat":  {"emitter": {"motion_amp": 0.5, "motion_speed": 0.3},
                   "motion": {"speed": 0.5}},

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
