"""OSC sender — bundles fast / slow features into UDP packets for Max.

Every audio block produces one OSC bundle (so all messages within a
block carry the same wallclock timetag and arrive at Max as a single
network packet). Bundles atomise CV / gate / RMS / etc. into individual
addressed messages inside the bundle.

OSC paths follow `/synapse/<feature>/<channel>` where channel is
**1-based** (matching how performers think of jacks; 0-based is an
implementation detail). One exception: edge events use
`/synapse/gate_event/<channel>` with payload `"rising"` or `"falling"`.

Throttle: CV values that haven't changed by more than `cv_eps` since
the last send are dropped from this block's bundle. Saves Max from
having to filter ~94Hz × N constant values; the moment the CV
actually moves the new value lands. `cv_eps=1e-3` gives enough
resolution for typical Eurorack LFO range without spamming Max.

Example bundle layout per block:

  [bundle, t=now]
    /synapse/rms/1        0.123
    /synapse/rms/2        0.456
    ...
    /synapse/centroid/1   2400.0
    ...
    /synapse/onset/1      0.0
    /synapse/onset/2      1.0  (this channel's onset envelope is hot)
    ...
    /synapse/cv/3         0.42         (only if changed since last send)
    /synapse/cv/4         -0.18
    /synapse/gate/1       1            (current state, every block)
    /synapse/gate/2       0
    /synapse/gate_event/1 rising       (only on edge)
    [/end bundle]
"""

from __future__ import annotations

import logging

import numpy as np
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.udp_client import UDPClient

from synapse.analysis.cv import CVFeatures
from synapse.analysis.gate import GateFeatures
from synapse.audio.features_fast import FastFeatures

logger = logging.getLogger(__name__)


class OSCSender:
    """UDP OSC client wired to Max (or any OSC consumer).

    Constructor opens the UDP socket; `send_block(...)` packages all
    available features into a single timetagged bundle and ships it.
    Lightweight enough to call every audio block (~94Hz).
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9000
    DEFAULT_CV_EPS = 1e-3

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        cv_eps: float = DEFAULT_CV_EPS,
    ) -> None:
        self.host = host
        self.port = port
        self.cv_eps = cv_eps
        self.client = UDPClient(host, port)
        # Last-sent CV per (1-based) channel index, for throttling.
        self._last_cv: dict[int, float] = {}
        self.bundles_sent = 0
        self.messages_sent = 0

    def send_block(
        self,
        fast: FastFeatures,
        cv: CVFeatures | None = None,
        gate: GateFeatures | None = None,
    ) -> None:
        """Build one bundle from the current block's features and send.

        `fast` is required (RMS / centroid / onset for all channels);
        `cv` and `gate` are only present when their respective
        detectors are configured for one or more channels.
        """
        bundle = OscBundleBuilder(0)  # 0 = "send immediately"
        added = 0

        # ---- audio-y features per channel (1-based on the wire) ---- #
        rms = fast.rms or []
        peak = fast.peak or []
        centroid = fast.centroid or []
        onset = fast.onset_envelope or []
        for ch_idx, (r, p, c, o) in enumerate(zip(rms, peak, centroid, onset, strict=False)):
            ch1 = ch_idx + 1
            added += _add_msg(bundle, f"/synapse/rms/{ch1}", float(r))
            added += _add_msg(bundle, f"/synapse/peak/{ch1}", float(p))
            added += _add_msg(bundle, f"/synapse/centroid/{ch1}", float(c))
            added += _add_msg(bundle, f"/synapse/onset/{ch1}", float(o))

        # ---- CV: throttled (only when changed) ---- #
        if cv is not None:
            for ch_idx, value, rate in zip(
                cv.channel_indices, cv.values, cv.rates, strict=False
            ):
                ch1 = ch_idx + 1
                last = self._last_cv.get(ch1)
                if last is None or abs(value - last) >= self.cv_eps:
                    added += _add_msg(bundle, f"/synapse/cv/{ch1}", float(value))
                    self._last_cv[ch1] = value
                # Rate is also sent only when it's non-trivial; rate
                # converges to ~0 between movements so we get for-free
                # silence at rest.
                if abs(rate) >= self.cv_eps:
                    added += _add_msg(bundle, f"/synapse/cv_rate/{ch1}", float(rate))

        # ---- gate: state every block, edges only when fired ---- #
        if gate is not None:
            for ch_idx, state, rising, falling in zip(
                gate.channel_indices,
                gate.states,
                gate.rising_edges,
                gate.falling_edges,
                strict=False,
            ):
                ch1 = ch_idx + 1
                added += _add_msg(bundle, f"/synapse/gate/{ch1}", int(state))
                if rising:
                    added += _add_msg(bundle, f"/synapse/gate_event/{ch1}", "rising")
                if falling:
                    added += _add_msg(bundle, f"/synapse/gate_event/{ch1}", "falling")

        # ---- block heartbeat ---- #
        added += _add_msg(bundle, "/synapse/block", int(fast.block_count))

        if added == 0:
            return  # nothing to send (silent + no movement)
        try:
            self.client.send(bundle.build())
            self.bundles_sent += 1
            self.messages_sent += added
        except OSError as e:
            # Network failure shouldn't kill the audio thread.
            logger.warning("OSC send failed: %s", e)

    def send_slow(self, embedding: np.ndarray, model_name: str) -> None:
        """Send a CLAP slow-tier embedding as a single message.

        Called at ~1Hz from the slow tier worker. The embedding is a
        512-D float32 vector that we serialise as a flat OSC float
        list — Max's [oscparse] turns this into a 512-element list
        which can drive [jit.matrix] / Unreal blueprints.
        """
        builder = OscMessageBuilder("/synapse/clap")
        for v in embedding:
            builder.add_arg(float(v))
        builder.add_arg(model_name)
        try:
            self.client.send(builder.build())
            self.messages_sent += 1
        except OSError as e:
            logger.warning("OSC slow send failed: %s", e)


def _add_msg(bundle: OscBundleBuilder, address: str, value: object) -> int:
    """Add one message to the bundle. Returns 1 (count) on success.

    Type-tag is inferred by python-osc from the Python type — float,
    int, str all work. We never raise on bad payload; OSC must not
    crash the audio thread.
    """
    try:
        builder = OscMessageBuilder(address)
        builder.add_arg(value)
        bundle.add_content(builder.build())
        return 1
    except Exception:  # noqa: BLE001
        logger.exception("OSC build failed at %s", address)
        return 0
