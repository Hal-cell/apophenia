"""FastAPI server: localhost web meter + WebSocket fast-feature broadcast.

Surface:
    GET  /          → static `web/index.html` (level meter + spectrum view)
    GET  /static/*  → CSS / JS / SVG assets
    GET  /health    → liveness probe
    GET  /roles     → current channel role list
    POST /roles     → update one channel's role (live, takes effect on
                       the next audio block)
    WS   /ws        → JSON stream at `broadcast_hz` carrying the latest
                       `FastFeatures` payload (RMS / peak / centroid /
                       onset envelope + role-filtered cv / gate /
                       spectrum sub-payloads) + optional `slow` (CLAP).

The server is mostly a viewer; the only control surface is `/roles`
which lets the user reassign a channel's role (audio | cv | gate)
without restarting synapse. The audio loop snapshots roles once per
block, so changes are visible at most one block later (~10ms at
48kHz/512).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from synapse.audio.features_fast import FeatureBus
from synapse.audio.features_slow import SlowBus
from synapse.channels import ChannelRole, ChannelRolesController

WEB_DIR = Path(__file__).parent / "web"
logger = logging.getLogger(__name__)


def make_app(
    bus: FeatureBus,
    slow_bus: SlowBus | None = None,
    broadcast_hz: float = 30.0,
    roles_controller: ChannelRolesController | None = None,
) -> FastAPI:
    """Construct the FastAPI app.

    `bus` is the fast feature bus — populated by the audio capture
    thread, read from at `broadcast_hz` for the WebSocket stream.
    `slow_bus` is optional; when supplied each WS payload carries a
    `slow` field with the latest CLAP embedding metadata.
    `roles_controller` is optional; when supplied, GET / POST `/roles`
    are served and the controller is mutated by POST.
    """
    if broadcast_hz <= 0:
        raise ValueError("broadcast_hz must be > 0")
    period = 1.0 / broadcast_hz

    app = FastAPI(title="synapse · audio analysis", docs_url=None, redoc_url=None)

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
                "roles_active": roles_controller is not None,
            }
        )

    @app.get("/roles")
    async def get_roles() -> JSONResponse:
        if roles_controller is None:
            raise HTTPException(status_code=404, detail="roles controller not active")
        return JSONResponse(
            {
                "roles": [r.value for r in roles_controller.get()],
                "version": roles_controller.version(),
                "n_channels": roles_controller.n_channels,
                "valid_roles": [r.value for r in ChannelRole],
            }
        )

    @app.post("/roles")
    async def post_roles(payload: dict = Body(...)) -> JSONResponse:  # noqa: B008
        # B008 flags FastAPI's Body(...) default — but this is the
        # idiomatic FastAPI pattern; the call result is a metadata
        # marker, not a shared mutable.
        """Update channel roles. Two payload shapes accepted:

            {"channel": <0-based int>, "role": "audio"|"cv"|"gate"}
                — update one channel's role
            {"roles": ["audio", "cv", "gate", ...]}
                — replace the entire role list (length must match n_channels)
        """
        if roles_controller is None:
            raise HTTPException(status_code=404, detail="roles controller not active")
        try:
            if "channel" in payload and "role" in payload:
                ch = int(payload["channel"])
                role = str(payload["role"])
                roles_controller.set_one(ch, role)
            elif "roles" in payload:
                roles_list = payload["roles"]
                if not isinstance(roles_list, list):
                    raise ValueError("'roles' must be a list of strings")
                roles_controller.set_all(roles_list)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "expected payload {'channel': int, 'role': str} or "
                        "{'roles': [str, ...]}"
                    ),
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        logger.info(
            "roles updated → %s",
            [r.value for r in roles_controller.get()],
        )
        return JSONResponse(
            {
                "ok": True,
                "roles": [r.value for r in roles_controller.get()],
                "version": roles_controller.version(),
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
