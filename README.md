# apophenia

> *apophenia* — *the tendency to perceive meaningful patterns or connections in random or unrelated stimuli.*

Multi-channel audio-reactive AV instrument. Listens to a Eurorack rack via Expert Sleepers ES-9 (14 channels), drives a real-time visual pipeline that fuses GLSL shaders (audio-reactive structure) with diffusion-model output (text + audio-conditioned style). The performer steers the AI live via text prompts and parameter sliders rather than letting it auto-pilot.

> **Status**: kickoff — phase 0 only. Not usable yet. Watch the [roadmap](#roadmap).

## Hardware

- **V1 target**: M3 Max laptop + Expert Sleepers ES-9 (14×14 USB-C audio interface for Eurorack)
- **V2 target** (later): Raspberry Pi 5 + Hailo-8 HAT, no laptop on stage

## Quick start (V1, kickoff phase)

```bash
# Clone
git clone https://github.com/Hal-cell/apophenia
cd apophenia

# Install (Python 3.12+, uv recommended)
uv sync

# CLI runs but the visual engine is still a stub.
# Phase 0 ships a working AudioSource Protocol + Mock generator only.
uv run apophenia --help
uv run apophenia run --source mock
uv run apophenia run --source mock:drums
```

You don't need ES-9 to run any phase up to 8 — the `mock` source generates 14 synthetic channels you can develop against. See [audio-sources spec](https://github.com/Hal-cell/apophenia/blob/main/docs/audio-sources.md) once specs are mirrored here.

## Architecture

```
14ch from ES-9 (or mock / file / BlackHole)
   │
   ▼
M3 Max laptop, three Python processes:

  audio_proc    fast features (~100Hz)  ─OSC─┐
                slow CLAP embed (~1Hz)  ─OSC─┤
                                              │
  control_proc  text prompts + 25 sliders  ──OSC── render_proc
                via FastAPI + web UI                ├─ moderngl shader engine (60fps)
                                                    ├─ SDXL-Turbo on MPS (15-20fps)
                                                    └─ composite + post-FX
                                                          │
                                                          ▼
                                                      HDMI → projector / screen
```

Two-stream visual: shader = **structure** driven by audio, AI = **style** driven by text + audio embedding. The composite blend ratio is a live performance knob.

## Roadmap

V1 = laptop-only, ~10 weekends. ES-9 not required for phases 0–8 (use mock / file / BlackHole 16ch + DAW).

| Phase | Title | Status | Tag |
|:---:|---|:---:|---|
| 0 | Kickoff: vault + repo + specs | ✅ | `v0-skeleton` |
| 1 | Mock + 14ch level meter | | `v1-mock` |
| 2 | Fast features (onset / centroid) | | `v2-features-fast` |
| 3 | Shader engine v0 | | `v3-shader` |
| 4 | CLAP slow tier | | `v4-clap` |
| 5 | Control UI v1 (text + sliders) | | `v5-control` |
| 6 | AI visual: SDXL-Turbo | | `v6-ai` |
| 7 | Composite + post-FX | | `v7-composite` |
| 8 | Polish + demo | | `v1-shipped` |

V1.5+ adds ControlNet structure injection, brush canvas, Whisper voice prompts. V2 ports to Pi 5 + Hailo.

## Why "apophenia"

The visual model is literally doing apophenia: it stares at audio embeddings (high-dimensional noise from a vision model's perspective) and projects meaningful images onto them. The performer biases what counts as "meaningful" via text prompts and parameter knobs. The whole instrument is a controlled version of this cognitive phenomenon.

## License

MIT.
