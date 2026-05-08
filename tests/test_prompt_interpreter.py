"""Tests for the keyword-based PromptInterpreter."""

from __future__ import annotations

from apophenia.prompt.interpreter import VOCABULARY, PromptInterpreter
from apophenia.state import VisualState


def test_empty_prompt_returns_empty_diff() -> None:
    r = PromptInterpreter().interpret("")
    assert r["matched"] == []
    assert r["partial"] == {}


def test_unknown_words_silently_ignored() -> None:
    r = PromptInterpreter().interpret("frobnicate the gibsonization quizzically")
    assert r["matched"] == []
    assert r["partial"] == {}


def test_single_known_keyword() -> None:
    r = PromptInterpreter().interpret("slow")
    assert r["matched"] == ["slow"]
    assert r["partial"] == {"motion": {"speed": 0.4}}


def test_keyword_composition_deep_merges() -> None:
    """Two tokens that touch different motion sub-fields should merge,
    not clobber each other."""
    r = PromptInterpreter().interpret("slow dense")
    assert set(r["matched"]) == {"slow", "dense"}
    assert r["partial"] == {"motion": {"speed": 0.4, "density": 0.85}}


def test_keyword_composition_across_groups() -> None:
    """slow (motion) + warm (palette + mood) + bloom (motion) — all
    three diffs deep-merge into a single partial state dict."""
    r = PromptInterpreter().interpret("slow warm bloom")
    p = r["partial"]
    # bloom's motion fields override slow's speed (bloom comes last).
    assert p["motion"]["speed"] == 0.7
    assert p["motion"]["density"] == 0.6
    assert p["motion"]["onset_sensitivity"] == 1.4
    # warm's palette + mood survive.
    assert p["palette"]["hue"] == 0.05
    assert p["palette"]["saturation"] == 1.2
    assert p["mood"]["valence"] == 0.7


def test_later_token_overrides_earlier_on_same_field() -> None:
    """`slow fast` should resolve to `fast` — last one wins, the natural
    read of natural language."""
    r = PromptInterpreter().interpret("slow fast")
    assert r["partial"]["motion"]["speed"] == 1.6  # fast's value


def test_punctuation_stripped() -> None:
    r = PromptInterpreter().interpret("slow, warm! bloom.")
    assert set(r["matched"]) == {"slow", "warm", "bloom"}


def test_case_insensitive() -> None:
    r = PromptInterpreter().interpret("SLOW Warm BLOOM")
    assert set(r["matched"]) == {"slow", "warm", "bloom"}


def test_synonyms_map_same_diff() -> None:
    """`purple` and `violet` should produce identical state diffs."""
    a = PromptInterpreter().interpret("purple")
    b = PromptInterpreter().interpret("violet")
    assert a["partial"] == b["partial"]


def test_returned_partial_is_valid_state_diff() -> None:
    """For every keyword in the vocabulary, applying its diff to a
    default VisualState must produce a valid VisualState (no out-of-range
    values, no schema violations)."""
    base = VisualState().model_dump()
    for keyword, diff in VOCABULARY.items():
        merged = _deep_merge(base, diff)
        # If this raises, the vocabulary entry has drifted out of schema.
        VisualState.model_validate(merged), f"{keyword} produces invalid state"


def test_full_prompt_round_trip_through_state() -> None:
    """End-to-end: a multi-keyword prompt → interpreter → VisualState
    must validate cleanly."""
    base = VisualState().model_dump()
    r = PromptInterpreter().interpret(
        "slow warm bloom violet dense glitchy kaleido"
    )
    merged = _deep_merge(base, r["partial"])
    state = VisualState.model_validate(merged)
    # Spot-check a couple of fields landed.
    assert state.fx.kaleidoscope == 6
    assert state.fx.glitch >= 0.5
    assert state.palette.hue == 0.78  # violet wins over warm's 0.05


def test_matched_preserves_order() -> None:
    """Useful for UI feedback — show the matched keywords in the order
    they appeared so the performer can scan."""
    r = PromptInterpreter().interpret("dense slow warm")
    assert r["matched"] == ["dense", "slow", "warm"]


def test_custom_vocabulary_override() -> None:
    """Subclasses / tests can pass their own vocabulary dict."""
    custom = {"sparkle": {"palette": {"saturation": 1.7}}}
    r = PromptInterpreter(vocabulary=custom).interpret("sparkle slow")
    # `slow` is unknown in the custom vocab.
    assert r["matched"] == ["sparkle"]
    assert r["partial"] == {"palette": {"saturation": 1.7}}


def test_trail_vocabulary_writes_fx_trail() -> None:
    """Phase-11 trail keywords drive `fx.trail`."""
    interp = PromptInterpreter()
    for word in ("trail", "smear", "ghost", "echo", "sustained", "decay"):
        r = interp.interpret(word)
        assert r["matched"] == [word]
        assert "fx" in r["partial"]
        assert "trail" in r["partial"]["fx"]
        assert 0.0 < r["partial"]["fx"]["trail"] < 1.0


def test_smooth_clears_trail_too() -> None:
    """`smooth` is the post-FX kill switch — should also zero the trail."""
    r = PromptInterpreter().interpret("smooth")
    assert r["partial"]["fx"]["trail"] == 0.0
    assert r["partial"]["fx"]["glitch"] == 0.0
    assert r["partial"]["fx"]["chromatic"] == 0.0


def test_camera_vocabulary_writes_camera_state() -> None:
    """Phase-12 camera keywords drive `state.camera`."""
    r = PromptInterpreter().interpret("close overhead vortex")
    p = r["partial"]
    # close → distance=2.5; overhead → elevation=70; vortex → orbit_speed=0.25
    assert p["camera"]["distance"] == 2.5
    assert p["camera"]["elevation"] == 70.0
    assert p["camera"]["orbit_speed"] == 0.25
    assert p["camera"]["autorotate"] is True


def test_still_disables_autorotate() -> None:
    r = PromptInterpreter().interpret("still")
    assert r["partial"]["camera"]["autorotate"] is False


def test_camera_vocabulary_validates_against_camera_state() -> None:
    """Every camera-touching keyword's diff must validate against
    CameraState — guards against vocabulary drifting out of the schema."""
    from apophenia.prompt.interpreter import VOCABULARY
    from apophenia.state import CameraState

    for keyword, diff in VOCABULARY.items():
        if "camera" not in diff:
            continue
        # Apply on top of defaults; if a value is out-of-range Pydantic raises.
        merged = {**CameraState().model_dump(), **diff["camera"]}
        CameraState.model_validate(merged), f"{keyword!r} produces invalid camera state"


# ---- helper ---- #


def _deep_merge(base: dict, update: dict) -> dict:
    out = dict(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
