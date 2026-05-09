# conduit

Multichannel audio analyser → MaxMSP bridge.

Reads up to 14 channels of audio from a Core Audio device (Expert
Sleepers ES-9, BlackHole, Pro Tools Audio Bridge, anything class-
compliant) and continuously extracts:

- **CV** — slow-moving DC values per channel (Eurorack control voltage)
- **Gate** — binary on/off state + rising/falling edge events per channel
- **Spectrum** — FFT magnitude bins per channel (or summed mix)
- **Extras** — RMS, peak, spectral centroid, onset envelope per channel
- **CLAP** (optional) — 512-dim mood/genre audio embedding

Forwards everything to MaxMSP (or any OSC consumer) so you can route
the data into Unreal Engine, TouchDesigner, or any visual / generative
system you like. The browser-based meter is a viewer for sanity-
checking what's coming through; conduit itself does no rendering.

> **Status**: skeleton phase. The audio capture + feature pipeline +
> meter UI are working; CV / gate / spectrum extraction + OSC output
> are next.

## Project history

This project started as **apophenia** — an audio-reactive AV
instrument with a 14-layer GLSL shader engine, autopilot modulator,
and Gray-Scott reaction-diffusion. That work is preserved at the
`archive/apophenia-visual-instrument` git tag in case it's ever
useful for reference. The current direction is far more focused:
extract numeric data from audio, ship it cleanly over OSC, do
nothing else.

## Hardware

Anything class-compliant on macOS works. Tested:

- Expert Sleepers ES-9 (14×14 DC-coupled, ideal for CV/gate)
- Pro Tools Audio Bridge 16 (loopback from a DAW)
- BlackHole 16ch (virtual loopback)

Without hardware, `--source mock:drums` (or any of the mock patterns)
generates 14 synthetic channels for development.

## Install

```bash
git clone https://github.com/Hal-cell/apophenia
cd apophenia
uv sync                # base install
uv sync --extra clap   # + CLAP slow tier (~600MB on first run)
uv sync --extra dev    # + tests / linting
```

Note: the GitHub repo is still named `apophenia` from the previous
phase. The Python package is `conduit` (this is what you `import`
and what the CLI command is).

## Quick start

```bash
# Mock 14ch audio + meter web UI on http://127.0.0.1:8000
uv run conduit run --source mock:drums --no-clap

# Real device
uv run conduit run --source device:"Pro Tools Audio Bridge 16"

# List available audio devices
uv run conduit devices

# Headless audio sanity check (no UI)
uv run conduit smoke -s mock:drums
```

## CLI

| Command | Description |
|---|---|
| `conduit run` | Spin up audio capture + meter web UI |
| `conduit devices` | List Core Audio input devices (★ for multichannel) |
| `conduit smoke` | Pull frames for N seconds, print per-channel RMS table |
| `conduit version` | Package + dependency versions |
| `conduit config` | Resolved paths + default audio device |

## Architecture

```
ES-9 (or any class-compliant audio device)
   │ 14 ch @ 48kHz
   ▼
┌─ conduit ──────────────────────────────────────────────────────────┐
│                                                                    │
│  audio capture (sounddevice)  →  FastFeatures bus                  │
│      ├ RMS / peak / centroid / onset (per channel)                 │
│      ├ CV detection           ◄── (planned)                        │
│      ├ Gate detection         ◄── (planned)                        │
│      └ FFT spectrum           ◄── (planned)                        │
│                                                                    │
│  CLAP slow tier (optional)    →  SlowBus  ┐                        │
│      512-dim audio embedding  @ ~1Hz       │                       │
│                                            ▼                       │
│                              ┌─ FastAPI / WebSocket ──┐            │
│                              │ /          web meter   │            │
│                              │ /ws        live JSON   │            │
│                              │ /health    liveness    │            │
│                              └────────────────────────┘            │
│                                            │                       │
│                              ┌─ python-osc client ◄── (planned)    │
│                              │ /conduit/cv/N    float              │
│                              │ /conduit/gate/N  bool               │
│                              │ /conduit/gate_event/N rising/...    │
│                              │ /conduit/spectrum/N [bins...]       │
│                              │ /conduit/...                        │
│                              └────────────────────────┘            │
│                                            │                       │
└────────────────────────────────────────────┼───────────────────────┘
                                             ▼
                                    UDP :9000 → MaxMSP → Unreal
```

## License

MIT.
