"""Quick check that ES-9 (or any 14-channel device) is visible to Core Audio.

Phase 1.5 helper. Stub for now — runs `synapse devices` essentially.
"""

from __future__ import annotations

from synapse.audio.device import list_devices


def main() -> None:
    devs = list_devices()
    if not devs:
        print("no input devices found.")
        return
    print(f"{'idx':>3}  {'ch':>3}   {'sr':>8}   name")
    for d in devs:
        name = d["name"]
        marker = " ★" if any(s in name for s in ("ES-9", "BlackHole", "Pro Tools")) else ""
        print(
            f"{d['index']:>3}  {d['max_input_channels']:>3}   "
            f"{d['default_samplerate']:>6}Hz   {name}{marker}"
        )


if __name__ == "__main__":
    main()
