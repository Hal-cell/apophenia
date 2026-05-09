"""FastAPI server: localhost web meter + WebSocket fast-feature broadcast.

Phase-16 surface (post-pivot):
    GET  /        →  static `web/index.html` (level meter + spectrum view)
    GET  /static/*→  CSS / JS / SVG assets
    GET  /health  →  liveness probe
    WS   /ws      →  JSON stream at `broadcast_hz` carrying the latest
                      `FastFeatures` payload (RMS / peak / centroid /
                      onset envelope per channel) + optional `slow`
                      (CLAP) sub-payload when the slow tier is on.

The server is a *viewer* — it does not accept any control input. All
output to MaxMSP / external systems goes via OSC (see
`conduit.osc_out`); the web UI is for live audio-quality debugging
("is the right channel mapping plugged in?", "is gate triggering?",
"is the spectrum reasonable?").
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from conduit.audio.features_fast import FeatureBus
from conduit.audio.features_slow import SlowBus

WEB_DIR = Path(__file__).parent / "web"


def make_app(
    bus: FeatureBus,
    slow_bus: SlowBus | None = None,
    broadcast_hz: float = 30.0,
) -> FastAPI:
    """Construct the FastAPI app.

    `bus` is the fast feature bus — populated by the audio capture
    thread, read from at `broadcast_hz` for the WebSocket stream.
    `slow_bus` is optional; when supplied each WS payload carries a
    `slow` field with the latest CLAP embedding metadata.
    """
    if broadcast_hz <= 0:
        raise ValueError("broadcast_hz must be > 0")
    period = 1.0 / broadcast_hz

    app = FastAPI(title="conduit · audio analysis", docs_url=None, redoc_url=None)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    @app.get("/health")
    async def health() -> JSONResponse:
        latest = bus.latest()
        slow = slow_bus.latest() if slow_bus else None
        return JSONResponse(
            {
                "ok": True,
                "has_data": latest is not None,
                "block_count": latest.block_count if latest else 0,
                "slow_active": slow_bus is not None,
                "slow_updates": slow.update_count if slow else 0,
            }
        )

    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                features = bus.latest()
                if features is not None:
                    payload = features.to_dict()
                    if slow_bus is not None:
                        slow = slow_bus.latest()
                        payload["slow"] = slow.to_dict() if slow else None
                    else:
                        payload["slow"] = None
                    await websocket.send_json(payload)
                await asyncio.sleep(period)
        except WebSocketDisconnect:
            return

    return app
