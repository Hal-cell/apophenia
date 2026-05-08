# apophenia

> *apophenia* — *the tendency to perceive meaningful patterns or connections in random or unrelated stimuli.*

Multi-channel audio-reactive AV instrument. Listens to a Eurorack rack via Expert Sleepers ES-9 (14 channels), drives a real-time GLSL pipeline (5 audio-reactive shader presets composited over 14 layers, with kaleidoscope / glitch / chromatic / saturation post-FX). The performer steers the visual via text prompts that describe **motion / brightness / colour / energy trajectory** — a `PromptInterpreter` translates words like "slow warm bloom" into shader-parameter diffs.

> **Status**: V1.5 shipped (`v10-prompt-controller` / `v1.5.0`). The V1 SDXL-Turbo image-generation tier was replaced with a much smaller prompt → shader-parameter controller that aligns better with how the instrument is actually played: AI controls **how** the visuals move, not **what** is depicted.

## Hardware

- **V1 target**: M3 Max laptop + Expert Sleepers ES-9 (14×14 USB-C audio interface for Eurorack). Any class-compliant macOS audio interface with ≥14 input channels will also work (BlackHole 16ch, Pro Tools Audio Bridge, Loopback).
- **V2 target** (later): Raspberry Pi 5 + Hailo-8 HAT, no laptop on stage.

You don't need ES-9 to run anything — the `mock` source generates 14 synthetic channels (silence / sines / drums / pad / noise / sweep) for development.

## Install

```bash
git clone https://github.com/Hal-cell/apophenia
cd apophenia

# Python 3.12+, uv recommended.
uv sync                          # base install (audio + control UI)
uv sync --extra visuals          # + GLSL render window
uv sync --extra ai               # + SDXL-Turbo (~5GB on first run)
uv sync --extra visuals --extra ai --extra dev
```

The optional extras are split so a remote / headless / dev install doesn't have to download torch + diffusers.

## Quick start

```bash
# Headless: 14ch level meter + control UI in your browser, mock audio.
uv run apophenia run --source mock:drums --no-render --no-clap --no-ai

# Full: GLSL render window + CLAP audio embedding + SDXL-Turbo.
uv run apophenia run --source device:"Pro Tools Audio Bridge 16"

# List available audio devices (★ marks ES-9 / BlackHole / Pro Tools Audio Bridge).
uv run apophenia devices

# Show resolved paths and the active default audio device.
uv run apophenia config

# Print version + dep versions.
uv run apophenia version
```

The web UI is at <http://127.0.0.1:8000> — opens automatically unless `--no-browser`.

### Run flags

| Flag | Default | Description |
|---|---|---|
| `--source` | `mock` | `mock`, `mock:<pattern>`, `file:<path>`, `device:<name>` |
| `--port` | `8000` | HTTP / WebSocket port |
| `--render` / `--no-render` | on | GLSL render window. `--no-render` keeps just the meter + control UI |
| `--clap` / `--no-clap` | on | LAION-CLAP audio embedding @ ~1Hz (downloads ~600MB on first run) |
| `--ai` / `--no-ai` | off | SDXL-Turbo image generation (downloads ~5GB on first run) |
| `--ai-resolution` | 512 | SDXL output side length in px (square) |
| `--ai-min-period` | 0.0 | Floor on AI generation period; 0 = run as fast as the GPU allows |
| `--broadcast-hz` | 30.0 | WebSocket broadcast rate (decoupled from ~94Hz audio rate) |
| `--no-browser` | — | Don't auto-open the browser |

## Architecture

```
14ch from ES-9 (or mock / file / device)
   │
   ▼
┌───────────────────── M3 Max laptop, single Python process ─────────────────────┐
│                                                                                │
│  audio_thread (fast)  ─┐                                                       │
│    ~94Hz: RMS, peak,    │                                                      │
│    centroid, onset env  ├─→ FeatureBus ─┐                                      │
│                         │               │                                      │
│  audio_thread (slow) ───┤               ├─→ /ws @ 30Hz ─→ web UI               │
│    ~1Hz: CLAP 512-dim   │               │                                      │
│    embedding            ├─→ SlowBus ────┤                                      │
│                         │               │                                      │
│  ai_thread (optional) ──┤               ├─→ AIBus ───────┐                     │
│    SDXL-Turbo @ 5–15Hz  │               │                │                     │
│    on MPS, 1-step,      │   StateBus ───┴──→ /api/state  │                     │
│    text-conditioned     │   (control UI                  │                     │
│                         │    sliders/                    │                     │
│                         │    presets)                    │                     │
│                         │                                ▼                     │
│  main thread (Cocoa req.):  ShaderEngine ──→ FBO ──→ Compositor ──→ window    │
│                              14 layers      offscreen   kaleidoscope            │
│                              of 5 GLSL                  + glitch                │
│                              presets                    + chromatic             │
│                                                         + AI time-interp        │
│                                                         + saturation            │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                                       ▼
                              HDMI → projector / screen
```

Two-stream visual: **shader = structure** driven by audio (per-channel RMS + spectral centroid + onset envelope drive 14 GLSL layers), **AI = style** driven by text + the user's blend sliders. The composite blend ratio is a live performance knob (`state.blend.shader_ai`).

Time interpolation between successive SDXL frames means the visible AI cadence matches the render rate (60+ fps), not the gen rate (5–15 fps).

### Buses (single-slot mailbox pattern)

- **`FeatureBus`** — fast-tier audio features (RMS / peak / centroid / onset env) at ~94Hz
- **`SlowBus`** — CLAP 512-dim audio embedding at ~1Hz
- **`StateBus`** — full `VisualState` (text prompt + ~22 sliders + 14ch weights + FX), partial-update via `PATCH /api/state`
- **`AIBus`** — latest SDXL-Turbo frame (RGB uint8 array + metadata)

Each is a thread-safe single-slot — readers always get the latest, no queue, no history. Consumers (render loop, WS broadcaster, AI loop) are decoupled from producer cadence.

## Control UI

Single-page web app at the run port (default 8000):

- **Meters** — 14 vertical level bars; bar colour from spectral centroid (orange = bass, blue = bright); top-edge flash from per-channel onset envelope
- **CLAP heatmap** — 32-bar downsample of the 512-dim embedding; updates ~1Hz with model name + inference latency
- **Text & presets** — live prompt textarea; 8×2 grid of preset slots (click=recall, shift+click=save, alt+click=clear); 12 curated starter presets ship out of the box
- **Blends** — `audio↔text`, `clap↔clip`, `shader↔ai`, `cfg`, mood XY pad with `follow_audio` toggle
- **Channels** — 14 per-channel weight sliders
- **Palette / FX / transport** — hue, saturation, glitch, chromatic, kaleidoscope segments, freeze, clear

Patches go through `PATCH /api/state` (deep-merged + Pydantic-validated) — the schema in `apophenia.state.VisualState` is the single source of truth. External clients (TouchOSC, custom Max patches, etc.) can drive the same endpoint.

## Performance (M3 Max, 1080p)

| Tier | Cadence | Latency | Notes |
|---|---|---|---|
| Fast features | ~94 Hz | 0.5 ms / block | Hann-windowed FFT, per-block onset detection |
| CLAP embedding | ~1 Hz | 22 ms / inference | LAION-CLAP HTSAT, MPS-accelerated |
| SDXL-Turbo | 5–15 Hz | 70–200 ms / frame | 1-step, 512², MPS-accelerated |
| Render | 60–120 fps | <16 ms / frame | 14 shader layers + composite pass |
| Web UI | 30 Hz over WS | — | decoupled from audio rate |

## Project layout

```
apophenia/
  audio/         AudioSource Protocol + mock / file / device sources
                 + fast features (RMS, centroid, onset)
                 + slow features (CLAP encoder + AudioBuffer ring)
  ai/            SDXL-Turbo wrapper, AIBus, ai_loop daemon
  control/       FastAPI server + web UI + StateBus + 16-slot preset bank
                 + 12 curated starter presets
  visuals/       moderngl ShaderEngine (5 GLSL fragment presets shared
                 across 14 layers) + Compositor (kaleidoscope / glitch /
                 chromatic / time-interp / saturation)
  state.py       VisualState pydantic schema (the wire protocol)
  cli.py         typer entry point: run, devices, smoke, version, config
```

## Roadmap

V1 = laptop-only, two-stream visual (shader + AI parallel), intervention layer = text + sliders.

| Phase | Title | Status | Tag |
|:---:|---|:---:|---|
| 0 | Kickoff: vault + repo + specs | ✅ | `v0-skeleton` |
| 1 | Mock + 14ch level meter | ✅ | `v1-mock` |
| 1.5 | DeviceSource (real audio in) | ✅ | `v1.5-device-source` |
| 2 | Fast features (onset / centroid) | ✅ | `v2-features-fast` |
| 3 | Shader engine v0 | ✅ | `v3-shader` |
| 4 | CLAP slow tier | ✅ | `v4-clap` |
| 5 | Control UI v1 (text + sliders + presets) | ✅ | `v5-control` |
| 6 | AI visual: SDXL-Turbo + compositor | ✅ | `v6-ai` |
| 7 | Composite + post-FX (kaleido / glitch / chromatic / interp) | ✅ | `v7-composite` |
| 8 | Polish + 12-preset starter bank + CLI polish | ✅ | `v1-shipped` |

V1.5+ adds ControlNet structure injection, brush canvas, Whisper voice prompts, OSC bridge for TouchOSC. V2 ports to Pi 5 + Hailo-8.

## Tests

```bash
uv run pytest                    # 153+ tests; 1 skipped real-CLAP, 1 skipped real-SDXL
APOPHENIA_RUN_CLAP=1 uv run pytest tests/test_features_slow.py    # opt-in real CLAP
APOPHENIA_RUN_SDXL=1 uv run pytest tests/test_ai_loop.py          # opt-in real SDXL
```

GL-context tests (compositor + shader engine) auto-skip when no display is available, so CI hosts don't need to fake an X server.

## Why "apophenia"

The visual model is literally doing apophenia: it stares at audio embeddings (high-dimensional noise from a vision model's perspective) and projects meaningful images onto them. The performer biases what counts as "meaningful" via text prompts and parameter knobs. The whole instrument is a controlled version of this cognitive phenomenon.

## License

MIT.
