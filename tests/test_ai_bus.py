"""Tests for the AIBus mailbox + AIFrame schema."""

from __future__ import annotations

import threading

import numpy as np

from apophenia.ai.bus import AIBus, AIFrame


def _frame(gen_count: int = 1, prompt: str = "test") -> AIFrame:
    """Build a small but valid AIFrame for tests."""
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    return AIFrame(
        image=img,
        prompt=prompt,
        gen_count=gen_count,
        latency_ms=42.0,
        seed=99,
        model_name="stub",
    )


def test_bus_starts_empty() -> None:
    bus = AIBus()
    assert bus.latest() is None


def test_bus_publish_replace() -> None:
    bus = AIBus()
    bus.publish(_frame(gen_count=1, prompt="a"))
    bus.publish(_frame(gen_count=2, prompt="b"))
    latest = bus.latest()
    assert latest is not None
    assert latest.gen_count == 2
    assert latest.prompt == "b"


def test_frame_to_dict_excludes_image() -> None:
    """Image bytes are big and useless over WebSocket; metadata only."""
    f = _frame()
    d = f.to_dict()
    assert "image" not in d
    assert d["gen_count"] == 1
    assert d["prompt"] == "test"
    assert d["latency_ms"] == 42.0
    assert d["seed"] == 99
    assert d["model_name"] == "stub"
    assert d["image_shape"] == [8, 8, 3]


def test_bus_thread_safety() -> None:
    """Concurrent publishers + readers shouldn't tear or crash."""
    bus = AIBus()
    stop = threading.Event()
    errors: list[Exception] = []

    def writer(start: int) -> None:
        try:
            for i in range(200):
                if stop.is_set():
                    return
                bus.publish(_frame(gen_count=start + i))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def reader() -> None:
        try:
            for _ in range(200):
                if stop.is_set():
                    return
                _ = bus.latest()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ws = [threading.Thread(target=writer, args=(i * 1000,), daemon=True) for i in range(3)]
    rs = [threading.Thread(target=reader, daemon=True) for _ in range(3)]
    for t in ws + rs:
        t.start()
    for t in ws + rs:
        t.join(timeout=2.0)
    stop.set()
    assert not errors, f"thread errors: {errors}"


def test_image_array_shape_preserved() -> None:
    """Ensure no defensive copy mangles the array shape."""
    bus = AIBus()
    img = np.random.randint(0, 256, size=(64, 96, 3), dtype=np.uint8)
    bus.publish(AIFrame(image=img, gen_count=1))
    latest = bus.latest()
    assert latest is not None
    assert latest.image.shape == (64, 96, 3)
    assert latest.image.dtype == np.uint8
