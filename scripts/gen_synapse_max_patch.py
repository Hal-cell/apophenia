"""Generate a comprehensive synapse Max patch.

Routing approach (post-empirical):
    Max's [route] doesn't reliably do hierarchical OSC matching —
    `[route /synapse]` followed by `[route cv ...]` followed by
    `[route 1 ...]` doesn't always strip / match the way the docs
    suggest. We fall back to **full-address routing**: one route
    object per category, with every channel's full address as a
    matcher. e.g.

        [route /synapse/rms/1 /synapse/rms/2 ... /synapse/rms/14]

    Each outlet directly drives the corresponding channel's widget.
    Block heartbeat and CLAP are single-outlet routes.

Layout (top to bottom):
  1. Title + status row (bundles received + block #)
  2. [udpreceive 9000] — fans out to all per-category routes
  3. AUDIO section: 3 routes (rms / centroid / onset) + 14 columns
                    of (slider, centroid #, onset bang)
  4. CV section: 2 routes (cv / cv_rate) + 14 columns of (flonum, flonum)
  5. GATE section: 2 routes (gate / gate_event) + 14 columns of (toggle, bang)
  6. SPECTRUM section: 1 route + umenu selector + 32-bin multislider
  7. CLAP: 1 route + 512-bin multislider

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


def add_channel_route(rid: str, x: float, y: float, category: str):
    """Add a per-category route with all 14 channel addresses.

    e.g. category='rms' → `route /synapse/rms/1 ... /synapse/rms/14`.
    Caller wires each outlet (0..N-1) to its channel widget; outlet N
    is the "unmatched" outlet (we never wire it).
    """
    addresses = " ".join(f"/synapse/{category}/{i+1}" for i in range(N))
    add(box(
        id=rid, maxclass="newobj",
        text=f"route {addresses}",
        patching_rect=[x, y, GRID_W, 22.0],
        numinlets=1, numoutlets=N + 1,
        outlettype=[""] * (N + 1),
    ))
    add_line("udpreceive", 0, rid, 0)


# --- Title + description ----------------------------------------------------
add(box(
    id="title",
    maxclass="comment",
    text="synapse · MaxMSP receiver\n14ch audio analyser → OSC bundles on UDP 9000",
    patching_rect=[30.0, 15.0, 480.0, 40.0],
    fontsize=14.0,
    numinlets=1, numoutlets=0,
))

# Status: bundles received counter (driven by /synapse/block which is
# emitted exactly once per audio block / OSC bundle).
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


# --- udpreceive (single source) ---------------------------------------------
add(box(
    id="udpreceive",
    maxclass="newobj",
    text="udpreceive 9000",
    patching_rect=[30.0, 75.0, 130.0, 22.0],
    numinlets=1, numoutlets=1,
    outlettype=[""],
))


# --- Block heartbeat route → status counters --------------------------------
# (One outlet — matches /synapse/block exactly. Drives both the displayed
#  block# and the bundles-received counter, since the OSC schema guarantees
#  exactly one /synapse/block per bundle.)
add(box(
    id="rt-block", maxclass="newobj",
    text="route /synapse/block",
    patching_rect=[170.0, 75.0, 200.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", ""],
))
add_line("udpreceive", 0, "rt-block", 0)
add_line("rt-block", 0, "status-block", 0)
add_line("rt-block", 0, "status-tick", 0)
add_line("status-tick", 0, "status-counter", 0)
add_line("status-counter", 0, "status-count", 0)


# --- AUDIO section ----------------------------------------------------------
AUDIO_ROUTES_TOP = 130
GRID_TOP = 220

add(box(
    id="hdr-meter", maxclass="comment",
    text="◆ AUDIO  RMS sliders · centroid # · onset bang",
    patching_rect=[30.0, AUDIO_ROUTES_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

# Three category routes, stacked. Each has 14 outlets driving the
# matching channel column's widget.
add_channel_route("rt-rms", 30, AUDIO_ROUTES_TOP, "rms")
add_channel_route("rt-centroid", 30, AUDIO_ROUTES_TOP + 30, "centroid")
add_channel_route("rt-onset", 30, AUDIO_ROUTES_TOP + 60, "onset")

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
CV_ROUTES_TOP = GRID_TOP + 290
CV_TOP = CV_ROUTES_TOP + 60

add(box(
    id="hdr-cv", maxclass="comment",
    text="◆ CV  smoothed DC value · rate of change",
    patching_rect=[30.0, CV_ROUTES_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_channel_route("rt-cv", 30, CV_ROUTES_TOP, "cv")
add_channel_route("rt-cv-rate", 30, CV_ROUTES_TOP + 30, "cv_rate")

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
GATE_ROUTES_TOP = CV_TOP + 100
GATE_TOP = GATE_ROUTES_TOP + 60

add(box(
    id="hdr-gate", maxclass="comment",
    text="◆ GATE  state toggle · edge bang (any rising/falling edge)",
    patching_rect=[30.0, GATE_ROUTES_TOP - 22, 540.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_channel_route("rt-gate", 30, GATE_ROUTES_TOP, "gate")
add_channel_route("rt-gate-event", 30, GATE_ROUTES_TOP + 30, "gate_event")

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
SPEC_ROUTE_TOP = GATE_TOP + 110
SPEC_TOP = SPEC_ROUTE_TOP + 30

add(box(
    id="hdr-spec", maxclass="comment",
    text="◆ SPECTRUM  pick a channel (only audio-role channels emit) · 32 log-spaced bins · ~30Hz",
    patching_rect=[30.0, SPEC_ROUTE_TOP - 22, 700.0, 20.0],
    numinlets=1, numoutlets=0,
))

add_channel_route("rt-spectrum", 30, SPEC_ROUTE_TOP, "spectrum")

# umenu lets the user pick which channel's spectrum to view.
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

# Multislider receiving the spectrum data.
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

# Per-channel gate: only let through messages from the selected channel.
# Each spec-gate is opened/closed by a [sel i] from umenu.
for i in range(N):
    x = 30 + (i // 2) * 60
    y = SPEC_TOP + 165 + (i % 2) * 70
    add(box(
        id=f"spec-sel-{i}", maxclass="newobj",
        text=f"sel {i}",
        patching_rect=[x, y, 40.0, 22.0],
        numinlets=2, numoutlets=2, outlettype=["bang", ""],
    ))
    add(box(
        id=f"spec-t-{i}", maxclass="newobj",
        text="t 1",
        patching_rect=[x, y + 24, 30.0, 22.0],
        numinlets=1, numoutlets=1, outlettype=["int"],
    ))
    add(box(
        id=f"spec-gate-{i}", maxclass="newobj",
        text="gate",
        patching_rect=[x, y + 48, 50.0, 22.0],
        numinlets=2, numoutlets=1, outlettype=[""],
    ))

    add_line("spec-menu", 0, f"spec-sel-{i}", 0)
    add_line(f"spec-sel-{i}", 0, f"spec-t-{i}", 0)
    add_line(f"spec-t-{i}", 0, f"spec-gate-{i}", 0)
    # Spectrum messages for this channel feed the gate's right inlet.
    add_line("rt-spectrum", i, f"spec-gate-{i}", 1)
    # Open gate output → multislider.
    add_line(f"spec-gate-{i}", 0, "spec-multi", 0)

# Broadcast "close all" from umenu so non-matching gates close before the
# matching one opens.
add(box(
    id="spec-closer", maxclass="newobj", text="t 0",
    patching_rect=[150.0, SPEC_TOP + 165, 30.0, 22.0],
    numinlets=1, numoutlets=1, outlettype=["int"],
))
add_line("spec-menu", 0, "spec-closer", 0)
for i in range(N):
    add_line("spec-closer", 0, f"spec-gate-{i}", 0)


# --- CLAP -------------------------------------------------------------------
CLAP_ROUTE_TOP = SPEC_TOP + 320
CLAP_TOP = CLAP_ROUTE_TOP + 30

add(box(
    id="hdr-clap", maxclass="comment",
    text="◆ CLAP  512-D audio embedding (slow tier ~1Hz, only when --clap is on)",
    patching_rect=[30.0, CLAP_ROUTE_TOP - 22, 700.0, 20.0],
    numinlets=1, numoutlets=0,
))

# Single-address route — outlet 0 emits the message body (all 512 floats
# + the model-name string).
add(box(
    id="rt-clap", maxclass="newobj",
    text="route /synapse/clap",
    patching_rect=[30.0, CLAP_ROUTE_TOP, 200.0, 22.0],
    numinlets=1, numoutlets=2,
    outlettype=["", ""],
))
add_line("udpreceive", 0, "rt-clap", 0)

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
# /synapse/clap message payload is 512 floats + 1 string. zl group 512
# pulls just the floats.
add(box(
    id="clap-zl", maxclass="newobj",
    text="zl group 512",
    patching_rect=[30.0, CLAP_TOP + 90, 130.0, 22.0],
    numinlets=2, numoutlets=2, outlettype=["", ""],
))
add_line("rt-clap", 0, "clap-zl", 0)
add_line("clap-zl", 0, "clap-multi", 0)


# --- Footer info ------------------------------------------------------------
add(box(
    id="footer", maxclass="comment",
    text=(
        "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of the\n"
        "per-channel route outlets above. /synapse/cv/N for slow control, /gate/N for triggers,\n"
        "/spectrum/N for the bin lists. Full schema: docs/OSC_SCHEMA.md in the repo."
    ),
    patching_rect=[30.0, CLAP_TOP + 130, 1080.0, 60.0],
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
        "rect": [60.0, 60.0, 1200.0, max(CLAP_TOP + 220, 1200.0)],
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
                       "onset / CV / gate / spectrum / CLAP for every channel. "
                       "Uses full-address routing (one route object per "
                       "category, /synapse/<feat>/<ch> per outlet).",
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
