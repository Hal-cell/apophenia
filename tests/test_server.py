"""Tests for the FastAPI control server.

Uses FastAPI's TestClient (httpx-backed) for HTTP routes and the WebSocket
helper for the /ws stream. No real network — TestClient runs the ASGI app
in-process.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apophenia.audio.features_fast import FastFeatures, FeatureBus
from apophenia.control.server import make_app
from apophenia.control.state_bus import StateBus


def _bus_with(features: FastFeatures | None = None) -> FeatureBus:
    bus = FeatureBus()
    if features is not None:
        bus.publish(features)
    return bus


def test_index_returns_html() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus))
    r = client.get("/")
    assert r.status_code == 200
    assert "apophenia" in r.text.lower()
    # Phase 5 UI is the control panel — sanity check a couple of fixtures.
    assert "control" in r.text.lower()
    assert "preset" in r.text.lower()


def test_health_endpoint_no_data() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "has_data": False,
        "block_count": 0,
        "slow_active": False,
        "slow_updates": 0,
    }


def test_health_endpoint_with_data() -> None:
    bus = _bus_with(FastFeatures(rms=[0.1] * 14, block_count=42))
    client = TestClient(make_app(bus))
    r = client.get("/health")
    assert r.json() == {
        "ok": True,
        "has_data": True,
        "block_count": 42,
        "slow_active": False,
        "slow_updates": 0,
    }


def test_websocket_streams_features() -> None:
    """Open /ws, expect at least one JSON message with our test data.

    TestClient's websocket_connect is synchronous; it pulls one message
    and we close. The server runs make_app's broadcast loop in the same
    event loop the client is iterating, so the first message arrives
    within the first broadcast period (~33ms at 30Hz default).
    """
    bus = _bus_with(
        FastFeatures(
            rms=[0.05] * 14,
            peak=[0.1] * 14,
            block_count=7,
            timestamp=1.5,
            source_name="MockSource",
            sample_rate=48_000,
            block_size=512,
            n_channels=14,
        )
    )
    client = TestClient(make_app(bus, broadcast_hz=120))  # fast for test
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["block_count"] == 7
        assert msg["source_name"] == "MockSource"
        assert msg["n_channels"] == 14
        assert len(msg["rms"]) == 14
        assert msg["sample_rate"] == 48_000


def test_websocket_skips_when_no_data() -> None:
    """With an empty bus, /ws shouldn't crash — it just sleeps until data
    is available. Connect, wait a tick, disconnect.
    """
    bus = _bus_with()  # empty
    client = TestClient(make_app(bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        # No data → no message arrives. Closing the connection should
        # cause the server to exit the loop cleanly without raising.
        ws.close()
    # If we got here without an exception, behaviour is correct.


# --------------------------------------------------------------------------- #
# State API (Phase 5)
# --------------------------------------------------------------------------- #


def test_get_state_returns_default() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert body["blend"]["audio_text"] == 0.5
    assert body["transport"]["freeze"] is False
    assert len(body["channel_weight"]) == 14


def test_patch_state_partial_blend() -> None:
    bus = _bus_with()
    state_bus = StateBus()
    client = TestClient(make_app(bus, state_bus=state_bus))
    r = client.patch("/api/state", json={"blend": {"audio_text": 0.8}})
    assert r.status_code == 200
    body = r.json()
    assert body["blend"]["audio_text"] == 0.8
    # Untouched fields kept their defaults.
    assert body["motion"]["speed"] == 1.0
    # And StateBus reflects it.
    assert state_bus.get().blend.audio_text == 0.8


def test_patch_state_invalid_returns_422() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.patch("/api/state", json={"blend": {"audio_text": 5.0}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "errors" in detail


def test_patch_state_replaces_channel_weight_array() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    weights = [0.0] * 7 + [1.0] * 7
    r = client.patch("/api/state", json={"channel_weight": weights})
    assert r.status_code == 200
    assert r.json()["channel_weight"] == weights


def test_patch_state_text_prompt() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.patch("/api/state", json={"text": {"prompt": "deep violet"}})
    assert r.status_code == 200
    assert r.json()["text"]["prompt"] == "deep violet"


# --------------------------------------------------------------------------- #
# Preset API (Phase 5)
# --------------------------------------------------------------------------- #


def test_get_presets_initially_loads_starter_bank(tmp_path: Path) -> None:
    """First-launch experience: 12 starter slots filled, 4 empty."""
    bus = _bus_with()
    client = TestClient(make_app(bus, preset_path=tmp_path / "presets.json"))
    r = client.get("/api/presets")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert len(body["presets"]) == 16
    full = [p for p in body["presets"] if p["state"] is not None]
    empty = [p for p in body["presets"] if p["state"] is None]
    assert len(full) == 12
    assert len(empty) == 4


def test_save_recall_clear_round_trip(tmp_path: Path) -> None:
    state_bus = StateBus()
    state_bus.update({"blend": {"audio_text": 0.7}, "motion": {"speed": 1.5}})
    bus = _bus_with()
    client = TestClient(
        make_app(bus, state_bus=state_bus, preset_path=tmp_path / "presets.json")
    )

    # Save current state into slot 13 with a distinctive label (slot 13 is
    # empty in the starter bank, so we know we're testing fresh-save).
    r = client.post("/api/presets/13/save", json={"label": "user-test-save"})
    assert r.status_code == 200
    body = r.json()
    assert body["presets"][13]["label"] == "user-test-save"
    assert body["presets"][13]["state"]["blend"]["audio_text"] == 0.7
    assert body["presets"][13]["state"]["motion"]["speed"] == 1.5
    # File on disk too.
    assert (tmp_path / "presets.json").exists()

    # Mutate state, then recall — should restore.
    state_bus.update({"blend": {"audio_text": 0.1}, "motion": {"speed": 0.5}})
    assert state_bus.get().motion.speed == 0.5
    r = client.post("/api/presets/13/recall")
    assert r.status_code == 200
    assert r.json()["blend"]["audio_text"] == 0.7
    assert state_bus.get().motion.speed == 1.5

    # Clear it.
    r = client.post("/api/presets/13/clear")
    assert r.status_code == 200
    assert r.json()["presets"][13]["state"] is None


def test_recall_empty_slot_returns_404(tmp_path: Path) -> None:
    """Slot 15 is always empty in the starter bank — perfect for the
    "empty" 404 contract."""
    bus = _bus_with()
    client = TestClient(make_app(bus, preset_path=tmp_path / "presets.json"))
    r = client.post("/api/presets/15/recall")
    assert r.status_code == 404


def test_preset_index_out_of_range_returns_400(tmp_path: Path) -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, preset_path=tmp_path / "presets.json"))
    for idx in (-1, 16, 99):
        r = client.post(f"/api/presets/{idx}/recall")
        assert r.status_code == 400


def test_save_uses_default_label_when_omitted(tmp_path: Path) -> None:
    bus = _bus_with()
    client = TestClient(
        make_app(bus, state_bus=StateBus(), preset_path=tmp_path / "presets.json")
    )
    r = client.post("/api/presets/0/save")
    assert r.status_code == 200
    assert r.json()["presets"][0]["label"] == "preset 1"


def test_presets_persist_across_app_instances(tmp_path: Path) -> None:
    """Saving in one app and recreating with the same preset_path should
    surface the same bank — proves we're hitting disk, not just memory."""
    preset_path = tmp_path / "presets.json"
    bus = _bus_with()
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "molten cathedral"}})

    client_a = TestClient(make_app(bus, state_bus=state_bus, preset_path=preset_path))
    client_a.post("/api/presets/2/save", json={"label": "a"}).raise_for_status()

    # Fresh app, same path.
    client_b = TestClient(make_app(_bus_with(), preset_path=preset_path))
    body = client_b.get("/api/presets").json()
    assert body["presets"][2]["label"] == "a"
    assert body["presets"][2]["state"]["text"]["prompt"] == "molten cathedral"


# --------------------------------------------------------------------------- #
# WebSocket carries state (Phase 5)
# --------------------------------------------------------------------------- #


def test_websocket_payload_includes_state() -> None:
    bus = _bus_with(
        FastFeatures(
            rms=[0.05] * 14,
            block_count=1,
            n_channels=14,
        )
    )
    state_bus = StateBus()
    state_bus.update({"text": {"prompt": "deep violet"}, "blend": {"audio_text": 0.7}})
    client = TestClient(make_app(bus, state_bus=state_bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert "state" in msg
        assert msg["state"]["text"]["prompt"] == "deep violet"
        assert msg["state"]["blend"]["audio_text"] == 0.7


# --------------------------------------------------------------------------- #
# Prompt API (Phase 10)
# --------------------------------------------------------------------------- #


def test_prompt_endpoint_applies_motion_diff() -> None:
    bus = _bus_with()
    state_bus = StateBus()
    client = TestClient(make_app(bus, state_bus=state_bus))

    r = client.post("/api/prompt", json={"text": "slow warm bloom"})
    assert r.status_code == 200
    body = r.json()
    assert "slow" in body["matched"]
    assert "warm" in body["matched"]
    assert "bloom" in body["matched"]
    # `applied` carries only the interpreted diff (not the prompt itself).
    applied = body["applied"]
    assert applied["motion"]["speed"] < 1.0  # slow + bloom both push speed down/up
    assert applied["palette"]["hue"] == pytest.approx(0.05)
    # `state` carries the full new state, including text.prompt.
    assert body["state"]["text"]["prompt"] == "slow warm bloom"
    assert state_bus.get().text.prompt == "slow warm bloom"


def test_prompt_endpoint_unknown_words_silently_ignored() -> None:
    bus = _bus_with()
    state_bus = StateBus()
    client = TestClient(make_app(bus, state_bus=state_bus))

    r = client.post("/api/prompt", json={"text": "frobnicate the gibsonization"})
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] == []
    # No state changes.
    assert state_bus.get().motion.speed == 1.0
    # Prompt itself still saved.
    assert state_bus.get().text.prompt == "frobnicate the gibsonization"


def test_prompt_endpoint_rejects_non_string_text() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))

    r = client.post("/api/prompt", json={"text": 42})
    assert r.status_code == 422


def test_prompt_endpoint_empty_body_is_safe() -> None:
    """Empty body (no text key) interprets the empty string — no-op."""
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))

    r = client.post("/api/prompt", json={})
    assert r.status_code == 200
    assert r.json()["matched"] == []
