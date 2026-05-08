"""FastAPI server: localhost web UI + WebSocket fast-feature broadcast.

Phase 4 surface:
    GET  /            → static `web/index.html` (level-meter page)
    GET  /static/*    → static assets (CSS, JS) for future expansion
    GET  /health      → JSON liveness probe; reflects bus state
    WS   /ws          → JSON stream at `broadcast_hz`. Each message has
                        the full FastFeatures dict, plus a "slow" field
                        carrying the latest SlowFeatures snapshot if a
                        SlowBus was provided (else null).

Broadcast rate is decoupled from feature production:
    audio publishes ~94Hz fast and ~1Hz slow,
    UI consumes 30Hz, attaching whatever slow snapshot is current.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apophenia.audio.features_fast import FeatureBus
from apophenia.audio.features_slow import SlowBus

WEB_DIR = Path(__file__).parent / "web"


def make_app(
    bus: FeatureBus,
    slow_bus: SlowBus | None = None,
    broadcast_hz: float = 30.0,
) -> FastAPI:
    """Construct the FastAPI app instance.

    Factory style (not module-level singleton) so tests can build an app
    against a mock bus without sharing state with production runs.
    """
    if broadcast_hz <= 0:
        raise ValueError("broadcast_hz must be > 0")
    period = 1.0 / broadcast_hz

    app = FastAPI(title="apophenia control", docs_url=None, redoc_url=None)

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
