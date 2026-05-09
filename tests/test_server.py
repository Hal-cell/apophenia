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
    client = TestClient(make_app(bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["block_count"] == 7
        assert msg["source_name"] == "MockSource"
        assert msg["n_channels"] == 14
        assert len(msg["rms"]) == 14
        assert msg["sample_rate"] == 48_000


def test_websocket_skips_when_no_data() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        ws.close()


# --------------------------------------------------------------------------- #
# State API
# --------------------------------------------------------------------------- #


def test_get_state_returns_default() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert body["palette"]["saturation"] == 1.0
    assert body["transport"]["freeze"] is False
    assert len(body["channel_weight"]) == 14


def test_patch_state_partial_palette() -> None:
    bus = _bus_with()
    state_bus = StateBus()
    client = TestClient(make_app(bus, state_bus=state_bus))
    r = client.patch("/api/state", json={"palette": {"hue": 0.4}})
    assert r.status_code == 200
    body = r.json()
    assert body["palette"]["hue"] == 0.4
    assert body["palette"]["saturation"] == 1.0
    assert state_bus.get().palette.hue == 0.4


def test_patch_state_invalid_returns_422() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.patch("/api/state", json={"palette": {"hue": 5.0}})
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


def test_patch_state_fx_kaleidoscope() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus, state_bus=StateBus()))
    r = client.patch("/api/state", json={"fx": {"kaleidoscope": 6}})
    assert r.status_code == 200
    assert r.json()["fx"]["kaleidoscope"] == 6


# --------------------------------------------------------------------------- #
# Preset API
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
    state_bus.update({"palette": {"hue": 0.7}, "fx": {"kaleidoscope": 8}})
    bus = _bus_with()
    client = TestClient(
        make_app(bus, state_bus=state_bus, preset_path=tmp_path / "presets.json")
    )

    r = client.post("/api/presets/13/save", json={"label": "user-test-save"})
    assert r.status_code == 200
    body = r.json()
    assert body["presets"][13]["label"] == "user-test-save"
    assert body["presets"][13]["state"]["palette"]["hue"] == 0.7
    assert body["presets"][13]["state"]["fx"]["kaleidoscope"] == 8
    assert (tmp_path / "presets.json").exists()

    state_bus.update({"palette": {"hue": 0.1}, "fx": {"kaleidoscope": 1}})
    assert state_bus.get().fx.kaleidoscope == 1
    r = client.post("/api/presets/13/recall")
    assert r.status_code == 200
    assert r.json()["palette"]["hue"] == 0.7
    assert state_bus.get().fx.kaleidoscope == 8

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
    state_bus.update({"palette": {"hue": 0.42}})

    client_a = TestClient(make_app(bus, state_bus=state_bus, preset_path=preset_path))
    client_a.post("/api/presets/13/save", json={"label": "a"}).raise_for_status()

    client_b = TestClient(make_app(_bus_with(), preset_path=preset_path))
    body = client_b.get("/api/presets").json()
    assert body["presets"][13]["label"] == "a"
    assert body["presets"][13]["state"]["palette"]["hue"] == 0.42


def test_websocket_payload_includes_state() -> None:
    bus = _bus_with(
        FastFeatures(rms=[0.05] * 14, block_count=1, n_channels=14)
    )
    state_bus = StateBus()
    state_bus.update({"palette": {"hue": 0.7}, "fx": {"kaleidoscope": 4}})
    client = TestClient(make_app(bus, state_bus=state_bus, broadcast_hz=120))
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert "state" in msg
        assert msg["state"]["palette"]["hue"] == 0.7
        assert msg["state"]["fx"]["kaleidoscope"] == 4
