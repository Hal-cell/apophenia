"""Tests for OSC sender — uses a local UDP listener to verify what's
actually wire-format-correct on the network."""

from __future__ import annotations

import socket
import threading
import time

import numpy as np
import pytest
from pythonosc import osc_bundle, osc_message

from synapse.analysis.cv import CVFeatures
from synapse.analysis.gate import GateFeatures
from synapse.audio.features_fast import FastFeatures
from synapse.osc.sender import OSCSender


class _OSCListener:
    """Bind a local UDP socket, collect packets in a list. Used as the
    test target so we can assert what OSC messages OSCSender produced
    for a given input batch."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))  # 0 = OS-assigned free port
        self.sock.settimeout(1.0)
        self.port = self.sock.getsockname()[1]
        self.packets: list[bytes] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                data, _ = self.sock.recvfrom(65536)
                self.packets.append(data)
            except TimeoutError:
                continue
            except OSError:
                return

    def close(self) -> None:
        self._stop.set()
        self.sock.close()

    def messages(self) -> list[tuple[str, list]]:
        """Parse all received packets (each is a bundle) into flat
        `[(address, args), ...]` for assertion convenience."""
        out: list[tuple[str, list]] = []
        for data in self.packets:
            if osc_bundle.OscBundle.dgram_is_bundle(data):
                bundle = osc_bundle.OscBundle(data)
                for elem in bundle:
                    if isinstance(elem, osc_message.OscMessage):
                        out.append((elem.address, list(elem.params)))
            else:
                msg = osc_message.OscMessage(data)
                out.append((msg.address, list(msg.params)))
        return out


@pytest.fixture
def listener():
    lst = _OSCListener()
    yield lst
    lst.close()


def _fast(rms: list[float] | None = None, **kw) -> FastFeatures:
    rms = rms or [0.1] * 4
    return FastFeatures(
        rms=rms,
        peak=[r * 1.5 for r in rms],
        centroid=[1000.0] * len(rms),
        onset_envelope=[0.0] * len(rms),
        block_count=kw.get("block_count", 1),
        n_channels=len(rms),
    )


def test_send_block_emits_per_channel_messages(listener) -> None:
    sender = OSCSender(host="127.0.0.1", port=listener.port)
    sender.send_block(_fast(rms=[0.1, 0.2, 0.3, 0.4]))
    time.sleep(0.05)  # let the recv loop catch up
    msgs = listener.messages()
    addresses = {addr for addr, _ in msgs}
    # 4 channels × 4 features (rms / peak / centroid / onset) + 1 block
    expected_some = {
        "/synapse/rms/1", "/synapse/rms/2", "/synapse/rms/3", "/synapse/rms/4",
        "/synapse/peak/1", "/synapse/centroid/1", "/synapse/onset/1",
        "/synapse/block",
    }
    assert expected_some.issubset(addresses)


def test_cv_only_sent_when_changed(listener) -> None:
    """First block: CV value sent. Second block (same value): NOT sent.
    Third block (changed): sent again."""
    sender = OSCSender(host="127.0.0.1", port=listener.port, cv_eps=0.001)
    cv1 = CVFeatures(channel_indices=[0], values=[0.5], rates=[0.0])
    cv2 = CVFeatures(channel_indices=[0], values=[0.5], rates=[0.0])  # unchanged
    cv3 = CVFeatures(channel_indices=[0], values=[0.7], rates=[2.0])  # changed
    sender.send_block(_fast(rms=[0.1]), cv=cv1)
    time.sleep(0.02)
    sender.send_block(_fast(rms=[0.1]), cv=cv2)
    time.sleep(0.02)
    sender.send_block(_fast(rms=[0.1]), cv=cv3)
    time.sleep(0.05)
    addrs = [addr for addr, _ in listener.messages()]
    cv_count = sum(1 for a in addrs if a == "/synapse/cv/1")
    assert cv_count == 2, f"expected 2 CV messages (block 1 + block 3), got {cv_count}"


def test_gate_state_sent_every_block(listener) -> None:
    """Gate state is broadcast every block (unlike CV which throttles)."""
    sender = OSCSender(host="127.0.0.1", port=listener.port)
    g1 = GateFeatures(
        channel_indices=[0], states=[True], rising_edges=[True], falling_edges=[False]
    )
    g2 = GateFeatures(
        channel_indices=[0], states=[True], rising_edges=[False], falling_edges=[False]
    )
    sender.send_block(_fast(rms=[0.1]), gate=g1)
    time.sleep(0.02)
    sender.send_block(_fast(rms=[0.1]), gate=g2)
    time.sleep(0.05)
    msgs = listener.messages()
    gate_state_msgs = [m for m in msgs if m[0] == "/synapse/gate/1"]
    assert len(gate_state_msgs) == 2


def test_gate_edge_event_only_fires_on_transition(listener) -> None:
    """gate_event message only goes out when the rising/falling flag
    is True in that block's GateFeatures."""
    sender = OSCSender(host="127.0.0.1", port=listener.port)
    rising = GateFeatures(
        channel_indices=[0], states=[True], rising_edges=[True], falling_edges=[False]
    )
    sustained = GateFeatures(
        channel_indices=[0], states=[True], rising_edges=[False], falling_edges=[False]
    )
    falling = GateFeatures(
        channel_indices=[0], states=[False], rising_edges=[False], falling_edges=[True]
    )
    sender.send_block(_fast(rms=[0.1]), gate=rising)
    time.sleep(0.02)
    sender.send_block(_fast(rms=[0.1]), gate=sustained)
    time.sleep(0.02)
    sender.send_block(_fast(rms=[0.1]), gate=falling)
    time.sleep(0.05)
    msgs = listener.messages()
    events = [(addr, args) for addr, args in msgs if addr == "/synapse/gate_event/1"]
    assert len(events) == 2
    assert events[0][1] == ["rising"]
    assert events[1][1] == ["falling"]


def test_send_slow_emits_clap_message(listener) -> None:
    sender = OSCSender(host="127.0.0.1", port=listener.port)
    embed = np.linspace(-1.0, 1.0, 16, dtype=np.float32)
    sender.send_slow(embed, "fake/model")
    time.sleep(0.05)
    msgs = listener.messages()
    clap = [m for m in msgs if m[0] == "/synapse/clap"]
    assert len(clap) == 1
    args = clap[0][1]
    assert len(args) == 17  # 16 floats + model name
    assert args[-1] == "fake/model"


def test_failed_send_does_not_crash() -> None:
    """If the UDP send fails (e.g. bound to a closed socket somehow),
    the sender should log + continue, never raise into the audio thread."""
    sender = OSCSender(host="127.0.0.1", port=1)  # very likely closed
    # Should not raise — even if the OS rejects the send.
    sender.send_block(_fast(rms=[0.1]))
