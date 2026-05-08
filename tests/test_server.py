"""Tests for the FastAPI control server.

Uses FastAPI's TestClient (httpx-backed) for HTTP routes and the WebSocket
helper for the /ws stream. No real network — TestClient runs the ASGI app
in-process.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from apophenia.audio.features_fast import FastFeatures, FeatureBus
from apophenia.control.server import make_app


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
    assert "level meter" in r.text.lower()


def test_health_endpoint_no_data() -> None:
    bus = _bus_with()
    client = TestClient(make_app(bus))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "has_data": False, "block_count": 0}


def test_health_endpoint_with_data() -> None:
    bus = _bus_with(FastFeatures(rms=[0.1] * 14, block_count=42))
    client = TestClient(make_app(bus))
    r = client.get("/health")
    assert r.json() == {"ok": True, "has_data": True, "block_count": 42}


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
