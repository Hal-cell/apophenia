"""Generate a comprehensive synapse Max patch.

Routing: a single [v8 synapse_router.js] parses every incoming OSC
message and dispatches the payload to one of 10 outlets (one per
category). For per-channel features the JS prepends the channel
number to the value, then a small `[route 1 2 ... 14]` after each
outlet demuxes by integer — which Max's [route] handles reliably,
unlike chained slash-prefixed OSC routing.

Layout (top to bottom):
  1. Title + status row (bundles received + block #)
  2. [udpreceive 9000] → [v8 synapse_router.js]
  3. AUDIO   : 3 [route 1..14]   + 14 columns of (slider, centroid #, onset bang)
  4. CV      : 2 [route 1..14]   + 14 columns of (flonum, flonum)
  5. GATE    : 2 [route 1..14]   + 14 columns of (toggle, bang)
  6. SPECTRUM: umenu → v8 inlet1 + 32-bin multislider directly off v8
  7. CLAP    : zl group 512 → 512-bin multislider

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


def add_chmux(rid: str, x: float, y: float, src_id: str, src_outlet: int):
    """Add a channel demuxer `[route 1 2 ... 14]` reading from the v8
    output and emitting per-channel values on its 14 outlets.

    The 15th outlet (right-most) is the "no match" outlet — never wired.
    """
    add(box(
        id=rid, maxclass="newobj",
        text="route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
        patching_rect=[x, y, GRID_W, 22.0],
        numinlets=1, numoutlets=N + 1,
        outlettype=[""] * (N + 1),
    ))
    add_line(src_id, src_outlet, rid, 0)


# --- Title + description ----------------------------------------------------
add(box(
    id="title",
    maxclass="comment",
    text="synapse · MaxMSP receiver  —  14ch audio analyser → OSC bundles on UDP 9000\n"
         "OSC parsing happens in synapse_router.js; per-channel demux via [route 1..14].",
    patching_rect=[30.0, 15.0, 700.0, 40.0],
    fontsize=13.0,
    numinlets=1, numoutlets=0,
))

# --- Status row (bundles received + block #) --------------------------------
add(box(
    id="status-label",
    maxclass="comment",
    text="bundles received:",
    patching_rect=[760.0, 20.0, 130.0, 20.0],
    numinlets=1, numoutlets=0,
))
add(box(
    id="status-count",
    maxclass="number",
    patching_rect=[890.0, 20.0, 80.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", "bang"],
))
add(box(
    id="status-tick",
    maxclass="newobj",
    text="t b 0",
    patching_rect=[890.0, 50.0, 50.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["bang", "int"],
))
add(box(
    id="status-counter",
    maxclass="newobj",
    text="counter 0 999999",
    patching_rect=[890.0, 78.0, 100.0, 22.0],
    numinlets=5, numoutlets=4,
    outlettype=["int", "", "", "int"],
))
add(box(
    id="status-block-label",
    maxclass="comment",
    text="block #:",
    patching_rect=[990.0, 20.0, 60.0, 20.0],
    numinlets=1, numoutlets=0,
))
add(box(
    id="status-block",
    maxclass="number",
    patching_rect=[1050.0, 20.0, 90.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", "bang"],
))


# --- udpreceive + v8 router ------------------------------------------------
add(box(
    id="udpreceive",
    maxclass="newobj",
    text="udpreceive 9000",
    patching_rect=[30.0, 75.0, 130.0, 22.0],
    numinlets=1, numoutlets=1,
    outlettype=[""],
))
# v8 with 2 inlets, 10 outlets — see synapse_router.js header for the
# per-outlet contract.
add(box(
    id="v8-router",
    maxclass="newobj",
    text="v8 synapse_router.js",
    patching_rect=[30.0, 105.0, 1080.0, 22.0],
    numinlets=2, numoutlets=10,
    outlettype=[""] * 10,
))
add_line("udpreceive", 0, "v8-router", 0)
# Block heartbeat: v8 outlet 8 → both status-block AND the bundle counter
# (one /synapse/block per bundle).
add_line("v8-router", 8, "status-block", 0)
add_line("v8-router", 8, "status-tick", 0)
add_line("status-tick", 0, "status-counter", 0)
add_line("status-counter", 0, "status-count", 0)


# --- AUDIO section ----------------------------------------------------------
AUDIO_MUX_TOP = 150
GRID_TOP = 235

add(box(
    id="hdr-meter", maxclass="comment",
    text="◆ AUDIO  RMS sliders · centroid # · onset bang",
    patching_rect=[30.0, AUDIO_MUX_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_chmux("rt-rms", 30, AUDIO_MUX_TOP, "v8-router", 0)
add_chmux("rt-centroid", 30, AUDIO_MUX_TOP + 28, "v8-router", 1)
add_chmux("rt-onset", 30, AUDIO_MUX_TOP + 56, "v8-router", 2)

# Per-channel widgets: label, slider (rms), centroid number, onset button
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
        min=0.0, mult=300.0,
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


# --- CV section -------------------------------------------------------------
CV_MUX_TOP = GRID_TOP + 290
CV_TOP = CV_MUX_TOP + 60

add(box(
    id="hdr-cv", maxclass="comment",
    text="◆ CV  smoothed DC value · rate of change",
    patching_rect=[30.0, CV_MUX_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_chmux("rt-cv", 30, CV_MUX_TOP, "v8-router", 3)
add_chmux("rt-cv-rate", 30, CV_MUX_TOP + 28, "v8-router", 4)

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
    add(box(
        id=f"cv-rate-{i}", maxclass="flonum",
        patching_rect=[x, CV_TOP + 48, CELL_W, 22.0],
        numinlets=1, numoutlets=2, outlettype=["", "bang"],
    ))
    add_line("rt-cv-rate", i, f"cv-rate-{i}", 0)


# --- GATE section -----------------------------------------------------------
GATE_MUX_TOP = CV_TOP + 100
GATE_TOP = GATE_MUX_TOP + 60

add(box(
    id="hdr-gate", maxclass="comment",
    text="◆ GATE  state toggle · edge bang (any rising/falling edge)",
    patching_rect=[30.0, GATE_MUX_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_chmux("rt-gate", 30, GATE_MUX_TOP, "v8-router", 5)
add_chmux("rt-gate-event", 30, GATE_MUX_TOP + 28, "v8-router", 6)

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


# --- Spectrum section -------------------------------------------------------
# JS does the channel selection — umenu → v8 inlet 1, multislider hangs
# directly off v8 outlet 7 (only the selected channel emits there).
SPEC_TOP = GATE_TOP + 110

add(box(
    id="hdr-spec", maxclass="comment",
    text="◆ SPECTRUM  pick a channel (only audio-role channels emit) · 32 log-spaced bins · ~30Hz",
    patching_rect=[30.0, SPEC_TOP - 22, 700.0, 20.0],
    numinlets=1, numoutlets=0,
))

add(box(
    id="spec-menu", maxclass="umenu",
    patching_rect=[30.0, SPEC_TOP, 100.0, 22.0],
    numinlets=1, numoutlets=3,
    outlettype=["int", "", ""],
    items=[f"ch{i+1}" for i in range(N)],
))
add(box(
    id="spec-menu-label", maxclass="comment",
    text="← select channel  (sent to v8 inlet 1; JS converts 0-based umenu int to 1-based ch)",
    patching_rect=[140.0, SPEC_TOP + 2, 600.0, 18.0],
    numinlets=1, numoutlets=0,
))
# Wire umenu's int outlet → v8 inlet 1
add_line("spec-menu", 0, "v8-router", 1)

# Multislider: receives 32 floats every ~30Hz from v8 outlet 7,
# already filtered to the selected channel.
add(box(
    id="spec-multi", maxclass="multislider",
    patching_rect=[30.0, SPEC_TOP + 35, 1080.0, 120.0],
    numinlets=1, numoutlets=2, outlettype=["", "bang"],
    size=32,
    contdata=1,
    setminmax=[0.0, 1.0],
    slidercolor=[0.984, 0.949, 0.831, 1.0],
    bgcolor=[0.094, 0.094, 0.094, 1.0],
    setstyle=0,
    candicable=0,
))
add_line("v8-router", 7, "spec-multi", 0)


# --- CLAP -------------------------------------------------------------------
CLAP_TOP = SPEC_TOP + 175

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
# v8 outlet 9 emits a 513-element list (512 floats + model name). zl
# group 512 keeps just the floats; the model name falls off as the
# 513th element wouldn't fit.
add(box(
    id="clap-zl", maxclass="newobj",
    text="zl group 512",
    patching_rect=[30.0, CLAP_TOP + 90, 130.0, 22.0],
    numinlets=2, numoutlets=2, outlettype=["", ""],
))
add_line("v8-router", 9, "clap-zl", 0)
add_line("clap-zl", 0, "clap-multi", 0)


# --- Footer -----------------------------------------------------------------
add(box(
    id="footer", maxclass="comment",
    text=(
        "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of\n"
        "the [route 1..14] outlets above (or the v8 category outlets directly).\n"
        "/synapse/cv/N for slow control, /gate/N for triggers, /spectrum/N for the bin lists.\n"
        "Full schema: docs/OSC_SCHEMA.md."
    ),
    patching_rect=[30.0, CLAP_TOP + 130, 1080.0, 70.0],
    numinlets=1, numoutlets=0,
))


# --- Top-level patcher -------------------------------------------------------
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
                       "Reads bundles on UDP 9000, parses via "
                       "synapse_router.js (v8), demuxes by integer "
                       "channel via [route 1..14] per category.",
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
