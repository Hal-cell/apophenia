"""FastAPI server: localhost web UI + WebSocket fast-feature broadcast.

Phase 1 surface:
    GET  /            → static `web/index.html` (level-meter page)
    GET  /static/*    → static assets (CSS, JS) — currently unused, page
                        is self-contained, but mounted for future growth
    WS   /ws          → JSON stream of FastFeatures at `broadcast_hz`

Broadcast rate is decoupled from audio rate: audio publishes ~94Hz
(48kHz / 512 samples), UI consumes 30Hz. Readers seeing only the
latest snapshot in the bus is correct; UI doesn't need history.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apophenia.audio.features_fast import FeatureBus

WEB_DIR = Path(__file__).parent / "web"


def make_app(bus: FeatureBus, broadcast_hz: float = 30.0) -> FastAPI:
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
        return JSONResponse(
            {
                "ok": True,
                "has_data": latest is not None,
                "block_count": latest.block_count if latest else 0,
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
                    await websocket.send_json(features.to_dict())
                await asyncio.sleep(period)
        except WebSocketDisconnect:
            return

    return app
