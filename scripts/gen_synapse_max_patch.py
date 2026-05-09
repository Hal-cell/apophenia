"""Generate a comprehensive synapse Max patch.

Layout (top to bottom):
  1. Title + status row
  2. udpreceive → oscparse → route /synapse → route categories
  3. Per-channel meter grid (RMS slider, centroid #, onset bang) ×14
  4. Per-channel CV row (flonum + rate flonum) ×14
  5. Per-channel gate row (toggle + edge bang) ×14
  6. Spectrum: [umenu] channel selector → big multislider
  7. CLAP: 512-bin multislider

Outputs JSON to stdout — pipe to .maxpat file.
"""
from __future__ import annotations

import json
import sys

N = 14  # ES-9 channels
CELL_W = 75
CELL_GAP = 5
COL_X = lambda i: 30 + i * (CELL_W + CELL_GAP)  # noqa: E731
GRID_W = N * (CELL_W + CELL_GAP)


def box(**kw):
    return {"box": kw}


def line(src_id, src_outlet, dst_id, dst_inlet):
    return {
        "patchline": {
            "source": [src_id, src_outlet],
            "destination": [dst_id, dst_inlet],
        }
    }


boxes: list = []
lines: list = []


def add(b):
    boxes.append(b)
    return b["box"]["id"]


def add_line(src_id, src_outlet, dst_id, dst_inlet):
    lines.append(line(src_id, src_outlet, dst_id, dst_inlet))


# --- Title + description ----------------------------------------------------
add(box(
    id="title",
    maxclass="comment",
    text="synapse · MaxMSP receiver\n14ch audio analyser → OSC bundles on UDP 9000",
    patching_rect=[30.0, 15.0, 480.0, 40.0],
    fontsize=14.0,
    numinlets=1, numoutlets=0,
))

# Status: bundles received counter
add(box(
    id="status-label",
    maxclass="comment",
    text="bundles received:",
    patching_rect=[540.0, 20.0, 130.0, 20.0],
    numinlets=1, numoutlets=0,
))
add(box(
    id="status-count",
    maxclass="number",
    patching_rect=[670.0, 20.0, 80.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", "bang"],
))
add(box(
    id="status-tick",
    maxclass="newobj",
    text="t b 0",
    patching_rect=[670.0, 50.0, 50.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["bang", "int"],
))
add(box(
    id="status-counter",
    maxclass="newobj",
    text="counter 0 999999",
    patching_rect=[670.0, 78.0, 100.0, 22.0],
    numinlets=5, numoutlets=4,
    outlettype=["int", "", "", "int"],
))
# block heartbeat number
add(box(
    id="status-block-label",
    maxclass="comment",
    text="block #:",
    patching_rect=[770.0, 20.0, 60.0, 20.0],
    numinlets=1, numoutlets=0,
))
add(box(
    id="status-block",
    maxclass="number",
    patching_rect=[830.0, 20.0, 90.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", "bang"],
))


# --- OSC chain --------------------------------------------------------------
# udpreceive in Max 8+ auto-parses incoming OSC bundles into individual
# address-pattern Max messages on its outlet — no separate [oscparse]
# needed. Older Max / non-standard installs may need [oscparse] inserted
# between udpreceive and the first [route].
add(box(
    id="udpreceive",
    maxclass="newobj",
    text="udpreceive 9000",
    patching_rect=[30.0, 75.0, 130.0, 22.0],
    numinlets=1, numoutlets=1,
    outlettype=[""],
))
add(box(
    id="route-synapse",
    maxclass="newobj",
    text="route /synapse",
    patching_rect=[30.0, 105.0, 130.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", ""],
))
add(box(
    id="route-cat",
    maxclass="newobj",
    text="route cv cv_rate gate gate_event rms peak centroid onset spectrum block clap",
    patching_rect=[30.0, 135.0, 660.0, 22.0],
    numinlets=1, numoutlets=12,
    outlettype=[""] * 12,
))

add_line("udpreceive", 0, "route-synapse", 0)
add_line("route-synapse", 0, "route-cat", 0)
# Wire status counter: every incoming OSC message ticks the counter.
add_line("udpreceive", 0, "status-tick", 0)
add_line("status-tick", 0, "status-counter", 0)
add_line("status-counter", 0, "status-count", 0)
# block heartbeat: route-cat outlet 9 (block) → status-block
add_line("route-cat", 9, "status-block", 0)


# --- Channel sub-routers ----------------------------------------------------
# For every category we have channel-N suffix routing /1 .. /14.
# route-cat outlet order: cv(0) cv_rate(1) gate(2) gate_event(3) rms(4) peak(5)
#                         centroid(6) onset(7) spectrum(8) block(9) clap(10)

CH_ROUTE_TEXT = "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14"

def add_channel_router(rid: str, x: float, y: float, src_id: str, src_outlet: int):
    add(box(
        id=rid, maxclass="newobj", text=CH_ROUTE_TEXT,
        patching_rect=[x, y, 460.0, 22.0],
        numinlets=1, numoutlets=N + 1,
        outlettype=[""] * (N + 1),
    ))
    add_line(src_id, src_outlet, rid, 0)


# Spread these horizontally so the patch isn't too tall.
add_channel_router("rt-rms", 30, 220, "route-cat", 4)
add_channel_router("rt-centroid", 30, 250, "route-cat", 6)
add_channel_router("rt-onset", 30, 280, "route-cat", 7)
add_channel_router("rt-cv", 30, 310, "route-cat", 0)
add_channel_router("rt-cv-rate", 30, 340, "route-cat", 1)
add_channel_router("rt-gate", 30, 370, "route-cat", 2)
add_channel_router("rt-gate-event", 30, 400, "route-cat", 3)
add_channel_router("rt-spectrum", 30, 430, "route-cat", 8)


# --- Per-channel METER grid (RMS slider + centroid + onset) ----------------
GRID_TOP = 480

# Section header
add(box(
    id="hdr-meter", maxclass="comment",
    text="◆ AUDIO  RMS sliders · centroid # · onset bang",
    patching_rect=[30.0, GRID_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

# Per-channel: label, slider (rms), centroid number, onset button, role text
for i in range(N):
    x = COL_X(i)
    chnum = i + 1

    add(box(
        id=f"label-{i}", maxclass="comment", text=f"ch{chnum}",
        patching_rect=[x, GRID_TOP, CELL_W, 18.0],
        numinlets=1, numoutlets=0,
    ))
    # RMS slider — tall vertical
    add(box(
        id=f"rms-slider-{i}", maxclass="slider",
        patching_rect=[x + (CELL_W - 22) / 2, GRID_TOP + 22, 22.0, 130.0],
        numinlets=1, numoutlets=1, outlettype=["int"],
        size=128,
        floatoutput=0,
        min=0.0, mult=300.0,  # remap rms*300 → 0-128 visual, gives ~-60dB visible
    ))
    add_line("rt-rms", i, f"rms-slider-{i}", 0)
    # Centroid number
    add(box(
        id=f"centroid-{i}", maxclass="number",
        patching_rect=[x, GRID_TOP + 158, CELL_W, 22.0],
        numinlets=1, numoutlets=2, outlettype=["", "bang"],
    ))
    add_line("rt-centroid", i, f"centroid-{i}", 0)
    # Onset bang button (visual flash)
    add(box(
        id=f"onset-{i}", maxclass="button",
        patching_rect=[x + (CELL_W - 24) / 2, GRID_TOP + 185, 24.0, 24.0],
        numinlets=1, numoutlets=1, outlettype=["bang"],
    ))
    # Onset arrives as a float (envelope value) — convert to bang on > 0.5.
    # Simplest: feed flonum → if > 0.5 → bang. Use [> 0.5] + sel 1.
    add(box(
        id=f"onset-thresh-{i}", maxclass="newobj",
        text="> 0.5",
        patching_rect=[x, GRID_TOP + 215, 50.0, 22.0],
        numinlets=2, numoutlets=1, outlettype=["int"],
    ))
    add(box(
        id=f"onset-sel-{i}", maxclass="newobj",
        text="sel 1",
        patching_rect=[x, GRID_TOP + 240, 40.0, 22.0],
        numinlets=2, numoutlets=2, outlettype=["bang", ""],
    ))
    add_line("rt-onset", i, f"onset-thresh-{i}", 0)
    add_line(f"onset-thresh-{i}", 0, f"onset-sel-{i}", 0)
    add_line(f"onset-sel-{i}", 0, f"onset-{i}", 0)


# --- Per-channel CV row (value + rate) -------------------------------------
CV_TOP = GRID_TOP + 290

add(box(
    id="hdr-cv", maxclass="comment",
    text="◆ CV  smoothed DC value · rate of change",
    patching_rect=[30.0, CV_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

for i in range(N):
    x = COL_X(i)
    chnum = i + 1

    add(box(
        id=f"cv-label-{i}", maxclass="comment",
        text=f"ch{chnum}",
        patching_rect=[x, CV_TOP, CELL_W, 18.0],
        numinlets=1, numoutlets=0,
    ))
    add(box(
        id=f"cv-val-{i}", maxclass="flonum",
        patching_rect=[x, CV_TOP + 22, CELL_W, 22.0],
        numinlets=1, numoutlets=2, outlettype=["", "bang"],
    ))
    add_line("rt-cv", i, f"cv-val-{i}", 0)
    # Rate as a smaller flonum
    add(box(
        id=f"cv-rate-{i}", maxclass="flonum",
        patching_rect=[x, CV_TOP + 48, CELL_W, 22.0],
        numinlets=1, numoutlets=2, outlettype=["", "bang"],
    ))
    add_line("rt-cv-rate", i, f"cv-rate-{i}", 0)


# --- Per-channel GATE row (toggle + edge button) ---------------------------
GATE_TOP = CV_TOP + 100

add(box(
    id="hdr-gate", maxclass="comment",
    text="◆ GATE  state toggle · edge bang (any rising/falling edge)",
    patching_rect=[30.0, GATE_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

for i in range(N):
    x = COL_X(i)
    chnum = i + 1

    add(box(
        id=f"gate-label-{i}", maxclass="comment",
        text=f"ch{chnum}",
        patching_rect=[x, GATE_TOP, CELL_W, 18.0],
        numinlets=1, numoutlets=0,
    ))
    add(box(
        id=f"gate-toggle-{i}", maxclass="toggle",
        patching_rect=[x + (CELL_W - 28) / 2, GATE_TOP + 22, 28.0, 28.0],
        numinlets=1, numoutlets=1, outlettype=["int"],
        parameter_enable=0,
    ))
    add_line("rt-gate", i, f"gate-toggle-{i}", 0)
    add(box(
        id=f"gate-edge-{i}", maxclass="button",
        patching_rect=[x + (CELL_W - 24) / 2, GATE_TOP + 56, 24.0, 24.0],
        numinlets=1, numoutlets=1, outlettype=["bang"],
    ))
    add_line("rt-gate-event", i, f"gate-edge-{i}", 0)


# --- Spectrum (channel selector → big multislider) -------------------------
SPEC_TOP = GATE_TOP + 110

add(box(
    id="hdr-spec", maxclass="comment",
    text="◆ SPECTRUM  pick a channel (only audio-role channels emit) · 32 log-spaced bins · ~30Hz",
    patching_rect=[30.0, SPEC_TOP - 22, 700.0, 20.0],
    numinlets=1, numoutlets=0,
))

# umenu lets the user pick which channel's spectrum to view
add(box(
    id="spec-menu", maxclass="umenu",
    patching_rect=[30.0, SPEC_TOP, 100.0, 22.0],
    numinlets=1, numoutlets=3,
    outlettype=["int", "", ""],
    items=[f"ch{i+1}" for i in range(N)],
))
add(box(
    id="spec-menu-label", maxclass="comment",
    text="← select channel",
    patching_rect=[140.0, SPEC_TOP + 2, 200.0, 18.0],
    numinlets=1, numoutlets=0,
))

# gate object: only let through messages from the selected channel
# Pattern: each rt-spectrum outlet → [if $i1 == <ch> then 1 else 0]?
# Simpler approach: just send all 14 spectra into [gate 14 1], driven by
# the umenu's int output. gate 14 1: 14 inlets, 1 selected at a time.
# Actually [gate] in Max is "gate <n_outlets>": one inlet, n outlets.
# We want [router] / [matrix] / use [selector~] for signals, but for
# messages there's [route] (already used) or just connect every outlet
# directly to the multislider — the LATEST spectrum wins for that
# multislider. That breaks if multiple channels emit close together.
#
# Cleanest: 14 spectrum outlets → 14 [gate 1 1] each enabled by a
# [select <i>] from umenu. When umenu = 0, only gate-0 passes; etc.
# But with 14 outlets that's a lot of objects. Use [gswitch2] which is
# "two-input one-output gate by integer index" — extends to N inlets
# actually no, gswitch2 is exactly 2.
#
# Pragmatic: just connect every spectrum channel to the SAME multislider.
# The multislider only updates when a list of 32 floats arrives. If
# multiple channels are emitting (all in audio role), the multislider
# will rapidly cycle through them at ~30Hz × N — visually chaotic but
# functional. Add a simple selector: [gate 14 1] where the index is
# from umenu+1 (gate's outlet index is 1-based, 0=closed).
# We'll feed every channel into a separate [if-then-else]-equivalent.
# Easier: use 14 [gate 1 1] objects each gated by a [== i] from umenu.

# Strategy: simple [gate 1] per channel, opened/closed by sel from umenu
add(box(
    id="spec-multi", maxclass="multislider",
    patching_rect=[30.0, SPEC_TOP + 35, 660.0, 120.0],
    numinlets=1, numoutlets=2, outlettype=["", "bang"],
    size=32,
    contdata=1,
    setminmax=[0.0, 1.0],
    slidercolor=[0.984, 0.949, 0.831, 1.0],
    bgcolor=[0.094, 0.094, 0.094, 1.0],
    setstyle=0,
    candicable=0,
))

# 14 gates, one per channel, each opened only when umenu == channel
for i in range(N):
    x = 30 + i * 50
    add(box(
        id=f"spec-sel-{i}", maxclass="newobj",
        text=f"sel {i}",
        patching_rect=[x, SPEC_TOP + 165 + (i % 2) * 25, 40.0, 22.0],
        numinlets=2, numoutlets=2, outlettype=["bang", ""],
    ))
    add(box(
        id=f"spec-gate-{i}", maxclass="newobj",
        text="gate",
        patching_rect=[x, SPEC_TOP + 215 + (i % 2) * 25, 50.0, 22.0],
        numinlets=2, numoutlets=1, outlettype=[""],
    ))
    # umenu sends int → sel i → bang only when matching → set gate open
    # The pattern needs a number that means "open" — gate's left inlet
    # accepts 1 (open) / 0 (closed). Use [t 1] after sel.
    add(box(
        id=f"spec-t-{i}", maxclass="newobj",
        text="t 1",
        patching_rect=[x, SPEC_TOP + 190 + (i % 2) * 25, 30.0, 22.0],
        numinlets=1, numoutlets=1, outlettype=["int"],
    ))

    add_line("spec-menu", 0, f"spec-sel-{i}", 0)
    add_line(f"spec-sel-{i}", 0, f"spec-t-{i}", 0)
    add_line(f"spec-t-{i}", 0, f"spec-gate-{i}", 0)
    # also need to close all OTHER gates when we open one; simplest:
    # send 0 to every gate first via an "any change" route. We can use
    # a `t 0 0 0 ... 0 0` pattern but cleaner: close-all on every umenu
    # change.
    # We'll use `loadmess 0` style: add a [t 0] from umenu's output that
    # broadcasts 0 to every gate's left inlet first (close), then sel
    # opens just one. Need to ensure ordering — Max evaluates right to
    # left in a t object, so put the open last.

# Broadcast "close all" from umenu: a single [t 0] → every gate's first inlet
add(box(
    id="spec-closer", maxclass="newobj", text="t 0",
    patching_rect=[150.0, SPEC_TOP + 165, 30.0, 22.0],
    numinlets=1, numoutlets=1, outlettype=["int"],
))
add_line("spec-menu", 0, "spec-closer", 0)
for i in range(N):
    add_line("spec-closer", 0, f"spec-gate-{i}", 0)

# Each gate's right inlet receives spectrum messages from rt-spectrum.
# Each gate output → multislider (joining 14 sources to 1 destination).
for i in range(N):
    add_line("rt-spectrum", i, f"spec-gate-{i}", 1)
    add_line(f"spec-gate-{i}", 0, "spec-multi", 0)


# --- CLAP --------------------------------------------------------------------
CLAP_TOP = SPEC_TOP + 290

add(box(
    id="hdr-clap", maxclass="comment",
    text="◆ CLAP  512-D audio embedding (slow tier ~1Hz, only when --clap is on)",
    patching_rect=[30.0, CLAP_TOP - 22, 700.0, 20.0],
    numinlets=1, numoutlets=0,
))

add(box(
    id="clap-multi", maxclass="multislider",
    patching_rect=[30.0, CLAP_TOP, 1080.0, 80.0],
    numinlets=1, numoutlets=2, outlettype=["", "bang"],
    size=512,
    contdata=1,
    setminmax=[-1.0, 1.0],
    slidercolor=[0.65, 0.85, 0.95, 1.0],
    bgcolor=[0.094, 0.094, 0.094, 1.0],
    setstyle=0,
    candicable=0,
))
# /clap message has 512 floats + 1 string (model name). zl group 512
# pulls just the floats.
add(box(
    id="clap-zl", maxclass="newobj",
    text="zl group 512",
    patching_rect=[30.0, CLAP_TOP + 90, 130.0, 22.0],
    numinlets=2, numoutlets=2, outlettype=["", ""],
))
add_line("route-cat", 10, "clap-zl", 0)
add_line("clap-zl", 0, "clap-multi", 0)


# --- Footer info -------------------------------------------------------------
add(box(
    id="footer", maxclass="comment",
    text=(
        "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of\n"
        "the routed signals above. /synapse/cv/N for slow control, /gate/N for triggers,\n"
        "/spectrum/N for the bin lists. Full schema: docs/OSC_SCHEMA.md in the repo."
    ),
    patching_rect=[30.0, CLAP_TOP + 130, 1080.0, 60.0],
    numinlets=1, numoutlets=0,
))


# --- Top-level patcher --------------------------------------------------------
patch = {
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 8, "minor": 6, "revision": 0,
            "architecture": "x64", "modernui": 1,
        },
        "classnamespace": "box",
        "rect": [60.0, 60.0, 1200.0, max(CLAP_TOP + 220, 1100.0)],
        "bglocked": 0,
        "openinpresentation": 0,
        "default_fontsize": 11.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [15.0, 15.0],
        "gridsnaponopen": 1,
        "objectsnaponopen": 1,
        "statusbarvisible": 2,
        "toolbarvisible": 1,
        "lefttoolbarpinned": 0,
        "toptoolbarpinned": 0,
        "righttoolbarpinned": 0,
        "bottomtoolbarpinned": 0,
        "toolbars_unpinned_last_save": 0,
        "tallnewobj": 0,
        "boxanimatetime": 200,
        "enablehscroll": 1,
        "enablevscroll": 1,
        "devicewidth": 0.0,
        "description": "synapse — comprehensive 14-channel OSC receiver. "
                        "Reads bundles on UDP 9000, displays RMS / centroid / "
                        "onset / CV / gate / spectrum / CLAP for every channel.",
        "digest": "",
        "tags": "",
        "style": "",
        "subpatcher_template": "",
        "assistshowspatchername": 0,
        "boxes": boxes,
        "lines": lines,
    }
}

json.dump(patch, sys.stdout, indent="\t")
sys.stdout.write("\n")
