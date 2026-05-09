"""End-to-end tests for live channel-role switching.

Covers two surfaces:
  1. `fast_features_loop` reads the controller's snapshot per block
     and filters detector outputs accordingly — switching a channel's
     role mid-run changes which sub-payloads it appears in.
  2. The FastAPI `/roles` endpoint mutates the controller, validates
     payloads, and returns 404 when the controller isn't wired.
"""

from __future__ import annotations

import threading
import time

from fastapi.testclient import TestClient

from synapse.analysis import CVDetector, GateDetector, SpectrumDetector
from synapse.audio.features_fast import FeatureBus, fast_features_loop
from synapse.audio.mock import MockSource
from synapse.channels import ChannelRole, ChannelRolesController
from synapse.control.server import make_app

# --------------------------------------------------------------------------- #
# Loop-level live switching
# --------------------------------------------------------------------------- #


def _pad_roles(prefix: list[ChannelRole], n: int = 14) -> list[ChannelRole]:
    """Extend a role list with AUDIO entries up to the mock's 14 channels."""
    return prefix + [ChannelRole.AUDIO] * (n - len(prefix))


def _build_loop_with_controller(
    initial_roles: list[ChannelRole],
) -> tuple[ChannelRolesController, FeatureBus, threading.Event, threading.Thread, MockSource]:
    """MockSource is fixed at 14 channels; pad shorter role lists with audio."""
    src = MockSource(pattern="drums", block_size=256)
    n_ch = src.n_channels
    initial_padded = _pad_roles(initial_roles, n_ch)
    bus = FeatureBus()
    stop = threading.Event()
    controller = ChannelRolesController(initial_padded)
    block_rate = src.sample_rate / src.block_size
    all_ch = list(range(n_ch))
    cv_det = CVDetector(all_ch, block_rate_hz=block_rate)
    gate_det = GateDetector(all_ch)
    spec_det = SpectrumDetector(
        audio_channel_indices=all_ch,
        sample_rate=src.sample_rate,
        block_size=src.block_size,
    )
    t = threading.Thread(
        target=fast_features_loop,
        args=(src, bus, stop),
        kwargs={
            "cv_detector": cv_det,
            "gate_detector": gate_det,
            "spectrum_detector": spec_det,
            "roles_controller": controller,
        },
        daemon=True,
    )
    t.start()
    return controller, bus, stop, t, src


def _wait_for_block(bus: FeatureBus, min_block: int = 1, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        f = bus.latest()
        if f is not None and f.block_count >= min_block:
            return
        time.sleep(0.005)
    raise TimeoutError(f"no block >= {min_block} in {timeout}s")


def test_initial_roles_are_published() -> None:
    """Channels start in their assigned roles; CV/gate sub-payloads
    contain only the configured channels."""
    controller, bus, stop, thread, _src = _build_loop_with_controller(
        [ChannelRole.GATE, ChannelRole.CV, ChannelRole.AUDIO, ChannelRole.AUDIO]
    )
    try:
        _wait_for_block(bus)
        latest = bus.latest()
        assert latest is not None
        # First two channels assigned, rest pad to audio (14 total).
        assert latest.roles[:2] == ["gate", "cv"]
        assert all(r == "audio" for r in latest.roles[2:])
        assert latest.cv is not None
        assert latest.cv["cv_channels"] == [1]
        assert latest.gate is not None
        assert latest.gate["gate_channels"] == [0]
        # Spectrum is throttled but should appear within a few blocks
        # for audio channels [2..13].
        deadline = time.monotonic() + 1.0
        spectrum_seen = False
        while time.monotonic() < deadline:
            f = bus.latest()
            if f is not None and f.spectrum is not None:
                assert f.spectrum["spectrum_channels"] == list(range(2, 14))
                spectrum_seen = True
                break
            time.sleep(0.005)
        assert spectrum_seen, "spectrum never appeared"
    finally:
        stop.set()
        thread.join(timeout=1.0)


def test_role_switch_takes_effect_within_one_block() -> None:
    """Toggle ch0 from audio → gate; the next block's payload places
    it in the gate sub-payload and drops it from the spectrum sub-
    payload (where it used to be as audio)."""
    controller, bus, stop, thread, _src = _build_loop_with_controller([])
    try:
        _wait_for_block(bus)
        latest = bus.latest()
        assert latest is not None
        # All 14 channels start as audio.
        assert all(r == "audio" for r in latest.roles)
        assert latest.cv is None or latest.cv["cv_channels"] == []
        assert latest.gate is None or latest.gate["gate_channels"] == []

        # Flip ch0 to gate.
        controller.set_one(0, ChannelRole.GATE)
        switch_block = latest.block_count
        deadline = time.monotonic() + 1.0
        observed = None
        while time.monotonic() < deadline:
            f = bus.latest()
            if f is not None and f.block_count > switch_block + 1:
                observed = f
                break
            time.sleep(0.005)
        assert observed is not None, "no fresh block after role switch"
        assert observed.roles[0] == "gate"
        assert all(r == "audio" for r in observed.roles[1:])
        assert observed.gate is not None
        assert observed.gate["gate_channels"] == [0]
        # ch0 should no longer appear in spectrum (now audio = [1..13]).
        if observed.spectrum is not None:
            assert 0 not in observed.spectrum["spectrum_channels"]
    finally:
        stop.set()
        thread.join(timeout=1.0)


def test_role_swap_loses_old_role_payload() -> None:
    """A channel that was in CV but is now in audio drops out of the
    CV sub-payload in the very next block."""
    controller, bus, stop, thread, _src = _build_loop_with_controller(
        [ChannelRole.CV, ChannelRole.CV, ChannelRole.AUDIO, ChannelRole.AUDIO]
    )
    try:
        _wait_for_block(bus)
        latest = bus.latest()
        assert latest is not None
        assert latest.cv is not None
        assert sorted(latest.cv["cv_channels"]) == [0, 1]

        # Flip ch0 to audio — should leave the CV payload entirely.
        controller.set_one(0, ChannelRole.AUDIO)
        switch_block = latest.block_count
        deadline = time.monotonic() + 1.0
        observed = None
        while time.monotonic() < deadline:
            f = bus.latest()
            if f is not None and f.block_count > switch_block + 1:
                observed = f
                break
            time.sleep(0.005)
        assert observed is not None
        assert observed.roles[0] == "audio"
        assert observed.cv is not None
        assert observed.cv["cv_channels"] == [1]  # ch0 no longer here
    finally:
        stop.set()
        thread.join(timeout=1.0)


def test_default_no_controller_publishes_all_audio() -> None:
    """When the loop is built without a controller, every channel is
    treated as audio — no cv/gate sub-payloads."""
    src = MockSource(pattern="drums", block_size=256)
    bus = FeatureBus()
    stop = threading.Event()
    block_rate = src.sample_rate / src.block_size
    all_ch = list(range(src.n_channels))
    spec_det = SpectrumDetector(
        audio_channel_indices=all_ch,
        sample_rate=src.sample_rate,
        block_size=src.block_size,
    )
    t = threading.Thread(
        target=fast_features_loop,
        args=(src, bus, stop),
        kwargs={
            "cv_detector": CVDetector(all_ch, block_rate_hz=block_rate),
            "gate_detector": GateDetector(all_ch),
            "spectrum_detector": spec_det,
            # NO roles_controller
        },
        daemon=True,
    )
    t.start()
    try:
        _wait_for_block(bus)
        latest = bus.latest()
        assert latest is not None
        assert all(r == "audio" for r in latest.roles)
        # No CV / gate channels => sub-payloads are None.
        assert latest.cv is None
        assert latest.gate is None
    finally:
        stop.set()
        t.join(timeout=1.0)


# --------------------------------------------------------------------------- #
# /roles HTTP endpoint
# --------------------------------------------------------------------------- #


def test_get_roles_returns_current_state() -> None:
    controller = ChannelRolesController(
        [ChannelRole.AUDIO, ChannelRole.CV, ChannelRole.GATE]
    )
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.get("/roles")
        assert r.status_code == 200
        body = r.json()
        assert body["roles"] == ["audio", "cv", "gate"]
        assert body["n_channels"] == 3
        assert body["version"] == 0
        assert sorted(body["valid_roles"]) == ["audio", "cv", "gate"]


def test_post_roles_single_channel_mutates_controller() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post("/roles", json={"channel": 2, "role": "gate"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["roles"] == ["audio", "audio", "gate", "audio"]
        assert body["version"] == 1
        # Controller is actually mutated.
        assert controller.role(2) == ChannelRole.GATE


def test_post_roles_full_list_replaces_state() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post(
            "/roles", json={"roles": ["gate", "gate", "cv", "cv"]}
        )
        assert r.status_code == 200
        assert controller.get() == [
            ChannelRole.GATE, ChannelRole.GATE, ChannelRole.CV, ChannelRole.CV,
        ]


def test_post_roles_rejects_bad_role_string() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post("/roles", json={"channel": 0, "role": "trigger"})
        assert r.status_code == 400
        assert "unknown role" in r.json()["detail"]


def test_post_roles_rejects_bad_index() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post("/roles", json={"channel": 99, "role": "cv"})
        assert r.status_code == 400
        assert "out of range" in r.json()["detail"]


def test_post_roles_rejects_length_mismatch() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post("/roles", json={"roles": ["audio", "cv"]})
        assert r.status_code == 400


def test_post_roles_rejects_unrecognised_payload() -> None:
    controller = ChannelRolesController([ChannelRole.AUDIO] * 4)
    bus = FeatureBus()
    app = make_app(bus, roles_controller=controller)
    with TestClient(app) as client:
        r = client.post("/roles", json={"frob": "knob"})
        assert r.status_code == 400


def test_roles_endpoints_404_when_controller_absent() -> None:
    """If make_app() didn't get a controller, /roles returns 404 to
    make the omission obvious instead of silently no-op'ing."""
    bus = FeatureBus()
    app = make_app(bus)  # no controller
    with TestClient(app) as client:
        assert client.get("/roles").status_code == 404
        assert client.post(
            "/roles", json={"channel": 0, "role": "cv"}
        ).status_code == 404
