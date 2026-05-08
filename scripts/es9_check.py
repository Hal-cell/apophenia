"""Quick check that ES-9 (or any 14-channel device) is visible to Core Audio.

Phase 1.5 helper. Stub for now — runs `apophenia devices` essentially.
"""

from __future__ import annotations

from apophenia.audio.device import list_devices


def main() -> None:
    names = list_devices()
    if not names:
        print("no input devices found.")
        return
    print("input devices:")
    for n in names:
        marker = " ★" if "ES-9" in n or "BlackHole" in n else ""
        print(f"  • {n}{marker}")


if __name__ == "__main__":
    main()
