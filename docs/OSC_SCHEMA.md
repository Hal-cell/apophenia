# synapse OSC schema

synapse sends one **OSC bundle per audio block** (~94Hz at 48kHz / 512-sample
blocks) to UDP port 9000 on the configured host (default `127.0.0.1`).
All addresses are 1-based for performer ergonomics — the channel
numbers match the panel jacks on your audio interface (ES-9 ch1 → OSC
`/synapse/.../1`).

Argument types: every value is a single OSC float (`f`), int (`i`), or
string (`s`). No nested arrays, no blobs.

## Per-channel features (every block)

| Address | Type | Range | Description |
|---|:---:|:---:|---|
| `/synapse/rms/N` | float | [0, ~1] | Per-block RMS amplitude on channel N |
| `/synapse/peak/N` | float | [0, ~1] | Per-block peak (max |sample|) on channel N |
| `/synapse/centroid/N` | float | [0, sr/2] Hz | Spectral centroid (brightness) on channel N |
| `/synapse/onset/N` | float | [0, 1] | Onset envelope — geometrically decays after each detected onset |

These four are emitted for **every** channel (regardless of role
assignment) since they're purely audio-domain features. CV / gate
channels carry CV / gate signals at audio rate, so RMS / centroid /
etc. of a CV channel are still sensible numbers — usually small and
flat for a stable CV, jumpy when the CV moves fast.

## CV channels (`--cv` flag)

Throttled — values are only emitted when they've changed by at least
`cv_eps` (default 1e-3) since the last send. This lets Max ignore
the noise floor for free.

| Address | Type | Range | Description |
|---|:---:|:---:|---|
| `/synapse/cv/N` | float | [-1, 1] | Smoothed DC value (single-pole IIR low-pass at ~30Hz cutoff) |
| `/synapse/cv_rate/N` | float | derivative units | dV/dt — only sent when |rate| > cv_eps |

## Gate channels (`--gate` flag)

State is broadcast every block; edge events fire only on the block
where the transition happens.

| Address | Type | Range | Description |
|---|:---:|:---:|---|
| `/synapse/gate/N` | int | 0 \| 1 | Current binary state |
| `/synapse/gate_event/N` | string | "rising" \| "falling" | Edge event — only on transition blocks |

Schmitt-triggered with hysteresis (default high=0.5, low=0.3) so
analog noise near the threshold doesn't toggle. Uses the per-block
peak (not mean) so brief Eurorack triggers (~2ms pulses inside an
~11ms block) still register.

## Spectrum (audio channels, throttled ~30Hz)

Each audio channel gets one OSC message per emission carrying all
N (default 32) log-spaced magnitude bins as float arguments.
Throttled to ~30Hz at the detector (configurable) — between
boundaries no spectrum messages are sent.

| Address | Type | Range | Description |
|---|:---:|:---:|---|
| `/synapse/spectrum/N` | float × n_bins | [0, 1] | Soft-compressed log-spaced magnitude bins (default 32 bins, fmin=20Hz → nyquist) |

In Max, parse with `[zl group 32]` after `[oscparse]` to recover the
32-element list, or hand directly to `[multislider]` for a one-line
spectrum view. Bin layout is documented as `bin_edges_hz` in the WS
payload (33 edges define 32 bins, geometrically spaced).

## Block heartbeat (every block)

| Address | Type | Description |
|---|:---:|---|
| `/synapse/block` | int | Monotonic block counter — useful for synchronisation / dropped-packet detection |

## CLAP slow tier (optional, ~1Hz)

Sent out of band — not in the per-block bundle, just a lone OSC
message at ~1Hz when CLAP inference completes.

| Address | Type | Description |
|---|:---:|---|
| `/synapse/clap` | float × 512 + string | 512-D audio embedding followed by the model name string |

## Bundle layout example

A typical bundle for a config of 14 channels with 2 gates (ch1, ch2),
3 CVs (ch3, ch4, ch5), and 9 audio channels (ch6..14), where ch1 just
went rising and ch3's CV moved:

```
[#bundle, t=0]
  /synapse/rms/1            0.012
  /synapse/peak/1           0.045
  /synapse/centroid/1       320.5
  /synapse/onset/1          0.0
  /synapse/rms/2            0.008
  ... (rms/peak/centroid/onset for every channel) ...
  /synapse/cv/3             0.42
  /synapse/cv_rate/3        1.8
  /synapse/gate/1           1
  /synapse/gate/2           0
  /synapse/gate_event/1     "rising"
  /synapse/spectrum/6       0.02 0.05 0.18 ... (32 floats, audio channels, throttled ~30Hz)
  /synapse/spectrum/7       0.01 0.04 0.21 ...
  /synapse/block            12345
[/bundle]
```

## Recommended Max routing pattern

```
[udpreceive 9000]
    │
    ▼
[oscparse]      ←── outputs (address pattern, args) per OSC message
    │
    ▼
[route /synapse]
    │
    ▼
[route cv gate gate_event rms peak centroid onset spectrum block clap]
   │   │     │            │   │     │       │     │        │     └───→ slow CLAP embedding
   │   │     │            │   │     │       │     │        └─────────→ block counter
   │   │     │            │   │     │       │     └──────────────────→ 32-bin spectrum (audio chs, ~30Hz)
   │   │     │            │   │     │       └────────────────────────→ onset envelope
   │   │     │            │   │     └────────────────────────────────→ centroid
   │   │     │            │   └──────────────────────────────────────→ peak
   │   │     │            └──────────────────────────────────────────→ RMS
   │   │     └───────────────────────────────────────────────────────→ "rising" / "falling" events
   │   └─────────────────────────────────────────────────────────────→ gate state (0/1)
   └─────────────────────────────────────────────────────────────────→ CV value
```

After the second `[route]` you'll have the channel number as the
address pattern's last part — use another `[route]` on `/1 /2 ...`
or `[zl]` / `[unpack]` to pick out specific channels.

## Re-broadcasting to Unreal

The simplest path is a forward-only `[udpsend]` per stream. Inside
Max, after parsing you can re-bundle with `[udpsend host port]` to
ship to whatever Unreal endpoint you've set up (typically a different
UDP port).
