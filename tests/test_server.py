"""Tests for the FastAPI control server.

Uses FastAPI's TestClient (httpx-backed) for HTTP routes and the WebSocket
helper for the /ws stream. No real network — TestClient runs the ASGI app
in-process.
"""

from __future__ import annotations

from pathlib import Path

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
        "ai_active": False,
        "ai_gens": 0,
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
        "ai_active": False,
        "ai_gens": 0,
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
    assert body["blend"]["clap_clip"] == 0.5
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


def test_get_presets_initially_empty(tmp_path: Path) -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, preset_path=tmp_path / "presets.json"))
    r = client.get("/api/presets")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert len(body["presets"]) == 16
    assert all(p["state"] is None for p in body["presets"])


def test_save_recall_clear_round_trip(tmp_path: Path) -> None:
    state_bus = StateBus()
    state_bus.update({"blend": {"audio_text": 0.7}, "cfg": 8.0})
    bus = _bus_with()
    client = TestClient(
        make_app(bus, state_bus=state_bus, preset_path=tmp_path / "presets.json")
    )

    # Save current state into slot 3 with a label.
    r = client.post("/api/presets/3/save", json={"label": "cathedral"})
    assert r.status_code == 200
    body = r.json()
    assert body["presets"][3]["label"] == "cathedral"
    assert body["presets"][3]["state"]["blend"]["audio_text"] == 0.7
    # File on disk too.
    assert (tmp_path / "presets.json").exists()

    # Mutate state, then recall — should restore.
    state_bus.update({"blend": {"audio_text": 0.1}, "cfg": 3.0})
    assert state_bus.get().cfg == 3.0
    r = client.post("/api/presets/3/recall")
    assert r.status_code == 200
    assert r.json()["blend"]["audio_text"] == 0.7
    assert state_bus.get().cfg == 8.0

    # Clear it.
    r = client.post("/api/presets/3/clear")
    assert r.status_code == 200
    assert r.json()["presets"][3]["state"] is None


def test_recall_empty_slot_returns_404(tmp_path: Path) -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, preset_path=tmp_path / "presets.json"))
    r = client.post("/api/presets/0/recall")
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
# AI tier (Phase 6)
# --------------------------------------------------------------------------- #


def test_health_reports_ai_inactive_by_default() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus))
    body = client.get("/health").json()
    assert body["ai_active"] is False
    assert body["ai_gens"] == 0


def test_health_reports_ai_active_when_bus_present() -> None:
    import numpy as np

    from apophenia.ai.bus import AIBus, AIFrame

    bus = _bus_with()
    ai_bus = AIBus()
    ai_bus.publish(
        AIFrame(image=np.zeros((4, 4, 3), dtype=np.uint8), gen_count=7, latency_ms=12.0)
    )
    client = TestClient(make_app(bus, ai_bus=ai_bus))
    body = client.get("/health").json()
    assert body["ai_active"] is True
    assert body["ai_gens"] == 7


def test_websocket_payload_includes_ai() -> None:
    import numpy as np

    from apophenia.ai.bus import AIBus, AIFrame

    bus = _bus_with(
        FastFeatures(rms=[0.05] * 14, block_count=1, n_channels=14)
    )
    ai_bus = AIBus()
    ai_bus.publish(
        AIFrame(
            image=np.zeros((8, 8, 3), dtype=np.uint8),
            prompt="test",
            gen_count=3,
            latency_ms=42.0,
            seed=99,
            model_name="stub",
        )
    )
    client = TestClient(make_app(bus, ai_bus=ai_bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert "ai" in msg
        assert msg["ai"]["gen_count"] == 3
        assert msg["ai"]["prompt"] == "test"
        assert msg["ai"]["latency_ms"] == 42.0
        # Image bytes must NOT make it through — too big for the wire.
        assert "image" not in msg["ai"]


def test_websocket_payload_ai_null_when_disabled() -> None:
    bus = _bus_with(
        FastFeatures(rms=[0.05] * 14, block_count=1, n_channels=14)
    )
    client = TestClient(make_app(bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert "ai" in msg
        assert msg["ai"] is None
