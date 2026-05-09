# synapse

Multichannel audio analyser → MaxMSP bridge.

Reads up to 14 channels of audio from a Core Audio device (Expert
Sleepers ES-9, BlackHole, Pro Tools Audio Bridge, anything class-
compliant) and continuously extracts:

- **CV** — smoothed DC values + rate of change per channel (Eurorack control voltage)
- **Gate** — Schmitt-triggered binary state + rising/falling edge events per channel
- **Spectrum** — 32 log-spaced FFT magnitude bins per audio channel @ ~30Hz
- **Extras** — RMS, peak, spectral centroid, onset envelope per channel (every block)
- **CLAP** (optional) — 512-dim mood/genre audio embedding @ ~1Hz

Forwards everything to MaxMSP (or any OSC consumer) so you can route
the data into Unreal Engine, TouchDesigner, or any visual / generative
system you like. The browser-based meter is a viewer for sanity-
checking what's coming through; synapse itself does no rendering.

OSC schema is documented in [`docs/OSC_SCHEMA.md`](docs/OSC_SCHEMA.md).
A starter Max patch is at [`examples/synapse_starter.maxpat`](examples/synapse_starter.maxpat).

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
phase. The Python package is `synapse` (this is what you `import`
and what the CLI command is).

## Quick start

```bash
# Mock 14ch audio + meter web UI on http://127.0.0.1:8000 + OSC → 127.0.0.1:9000
uv run synapse run --source mock:drums --no-clap

# Real ES-9 with channel role assignments (1-based, performer-friendly)
uv run synapse run \
    --source device:"ES-9" \
    --gate "1,2" \
    --cv "3-6" \
    --osc-host 127.0.0.1 --osc-port 9000

# Real device, OSC disabled (just web meter)
uv run synapse run --source device:"Pro Tools Audio Bridge 16" --no-osc

# List available audio devices
uv run synapse devices

# Headless audio sanity check (no UI)
uv run synapse smoke -s mock:drums
```

## CLI

| Command | Description |
|---|---|
| `synapse run` | Spin up audio capture + meter web UI + OSC sender |
| `synapse devices` | List Core Audio input devices (★ for multichannel) |
| `synapse smoke` | Pull frames for N seconds, print per-channel RMS table |
| `synapse version` | Package + dependency versions |
| `synapse config` | Resolved paths + default audio device |

### `synapse run` flags

| Flag | Default | Description |
|---|---|---|
| `--source` | `mock:drums` | `device:<name>`, `mock:<pattern>`, or `file:<path>` |
| `--gate <range>` | none | 1-based channels that carry Eurorack gates / triggers (e.g. `"1,2"`) |
| `--cv <range>` | none | 1-based channels that carry Eurorack CV (e.g. `"3-6"` or `"3,5,8"`) |
| `--audio <range>` | rest | 1-based channels for full audio analysis (default: anything not gate/cv) |
| `--osc-host` | `127.0.0.1` | Where to send OSC bundles |
| `--osc-port` | `9000` | UDP port to send OSC bundles to |
| `--no-osc` | off | Disable OSC sending entirely (web meter only) |
| `--no-clap` | off | Disable CLAP slow tier (skip 600MB model download) |
| `--no-browser` | off | Don't auto-open the web meter |

## Architecture

```
ES-9 (or any class-compliant audio device)
   │ 14 ch @ 48kHz
   ▼
┌─ synapse ──────────────────────────────────────────────────────────┐
│                                                                    │
│  audio capture (sounddevice)  →  FastFeatures bus                  │
│      ├ RMS / peak / centroid / onset (per channel)                 │
│      ├ CV detection           — IIR low-pass + dV/dt               │
│      ├ Gate detection         — Schmitt trigger + edge events      │
│      └ Spectrum               — 32 log-spaced bins @ ~30Hz         │
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
│                              ┌─ python-osc client ─────┐           │
│                              │ /synapse/cv/N      float (throttled)│
│                              │ /synapse/cv_rate/N float            │
│                              │ /synapse/gate/N    int 0|1          │
│                              │ /synapse/gate_event/N "rising"/...  │
│                              │ /synapse/rms|peak|centroid|onset/N  │
│                              │ /synapse/spectrum/N 32×float (~30Hz)│
│                              │ /synapse/block     int (heartbeat)  │
│                              │ /synapse/clap      512×float + name │
│                              └─────────────────────────┘           │
│                                            │                       │
└────────────────────────────────────────────┼───────────────────────┘
                                             ▼
                                    UDP :9000 → MaxMSP → Unreal
```

Full schema with addresses, ranges, and bundle layout:
[`docs/OSC_SCHEMA.md`](docs/OSC_SCHEMA.md).

## License

MIT.
