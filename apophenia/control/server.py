"""FastAPI server: localhost web UI + WebSocket fast-feature broadcast +
state / preset HTTP API.

Phase 10 surface (post AI/text strip):
    GET    /                  → static `web/index.html`
    GET    /static/*          → static assets (CSS, JS, etc.)
    GET    /health            → JSON liveness probe
    WS     /ws                → JSON stream at `broadcast_hz` carrying
                                 fast features + slow features + state
    GET    /api/state         → current `VisualState` as JSON
    PATCH  /api/state         → partial state update (deep-merged)
    GET    /api/presets       → all 16 preset slots
    POST   /api/presets/{idx}/save    → save current state into slot
    POST   /api/presets/{idx}/recall  → load slot into state
    POST   /api/presets/{idx}/clear   → empty the slot
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from apophenia.audio.features_fast import FeatureBus
from apophenia.audio.features_slow import SlowBus
from apophenia.control.presets import (
    PRESET_BANK_SIZE,
    PresetBank,
    clear_slot,
    save_slot,
)
from apophenia.control.presets import (
    load as load_bank,
)
from apophenia.control.presets import (
    save as save_bank,
)
from apophenia.control.state_bus import StateBus

WEB_DIR = Path(__file__).parent / "web"


def make_app(
    bus: FeatureBus,
    slow_bus: SlowBus | None = None,
    state_bus: StateBus | None = None,
    preset_path: Path | None = None,
    broadcast_hz: float = 30.0,
) -> FastAPI:
    """Construct the FastAPI app instance.

    `state_bus` and `preset_path` are optional; if omitted, a fresh
    `StateBus` is created and presets land at the default
    `~/.config/apophenia/presets.json`. Tests pass explicit instances
    so they don't trample the user's real preset bank.
    """
    if broadcast_hz <= 0:
        raise ValueError("broadcast_hz must be > 0")
    period = 1.0 / broadcast_hz
    if state_bus is None:
        state_bus = StateBus()

    bank_lock = threading.Lock()
    bank: list[PresetBank] = [load_bank(preset_path)]

    def _bank() -> PresetBank:
        return bank[0]

    def _set_bank(b: PresetBank) -> None:
        bank[0] = b

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

    @app.get("/api/state")
    async def get_state() -> JSONResponse:
        return JSONResponse(state_bus.get().model_dump())

    @app.patch("/api/state")
    async def patch_state(partial: dict[str, Any]) -> JSONResponse:
        """Deep-merge `partial` into the current state. Empty body → no-op."""
        try:
            new_state = state_bus.update(partial)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(include_url=False)},
            ) from e
        return JSONResponse(new_state.model_dump())

    def _check_idx(idx: int) -> None:
        if idx < 0 or idx >= PRESET_BANK_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"preset index {idx} out of range [0, {PRESET_BANK_SIZE})",
            )

    @app.get("/api/presets")
    async def get_presets() -> JSONResponse:
        with bank_lock:
            return JSONResponse(_bank().model_dump())

    @app.post("/api/presets/{idx}/save")
    async def save_preset(idx: int, body: dict[str, Any] | None = None) -> JSONResponse:
        _check_idx(idx)
        label = (body or {}).get("label")
        with bank_lock:
            new_bank = save_slot(_bank(), idx, state_bus.get(), label)
            _set_bank(new_bank)
            save_bank(new_bank, preset_path)
            return JSONResponse(new_bank.model_dump())

    @app.post("/api/presets/{idx}/recall")
    async def recall_preset(idx: int) -> JSONResponse:
        _check_idx(idx)
        with bank_lock:
            slot = _bank().presets[idx]
            if slot.state is None:
                raise HTTPException(status_code=404, detail=f"slot {idx} is empty")
            new_state = state_bus.replace(slot.state)
            return JSONResponse(new_state.model_dump())

    @app.post("/api/presets/{idx}/clear")
    async def clear_preset(idx: int) -> JSONResponse:
        _check_idx(idx)
        with bank_lock:
            new_bank = clear_slot(_bank(), idx)
            _set_bank(new_bank)
            save_bank(new_bank, preset_path)
            return JSONResponse(new_bank.model_dump())

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
                    payload["state"] = state_bus.get().model_dump()
                    await websocket.send_json(payload)
                await asyncio.sleep(period)
        except WebSocketDisconnect:
            return

    return app
