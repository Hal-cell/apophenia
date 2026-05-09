/**
 * synapse_router.js — single-object OSC dispatch for the synapse Max patch.
 *
 * Replaces the chain of [route] objects with explicit JS parsing.
 * Max's built-in [route] doesn't reliably do hierarchical OSC matching
 * across multiple chained stages (it's fine on full-address args but
 * the per-segment strip behaviour is unreliable in practice). This v8
 * object parses every incoming OSC message ONCE and dispatches the
 * payload onto a fixed per-category outlet, with the channel index
 * prepended as a list element. Downstream [route 1 2 ... 14] then
 * matches plain integers, which always works.
 *
 * Inlets:
 *   0 — raw OSC from [udpreceive 9000]
 *   1 — selected spectrum channel.
 *       Accepts either:
 *         * 0-based int (umenu output: 0..13 maps to ch1..ch14)
 *         * 1-based int sent as a 'set N' message (1..14)
 *       Internally stored as 1-based to match OSC addresses.
 *
 * Outlets (right-to-left order in Max — outlet 0 is leftmost):
 *   0 — rms        : list <channel-int> <value-float>
 *   1 — centroid   : list <channel-int> <value-float>
 *   2 — onset      : list <channel-int> <envelope-float>
 *   3 — cv         : list <channel-int> <value-float>
 *   4 — cv_rate    : list <channel-int> <rate-float>
 *   5 — gate       : list <channel-int> <state-int 0|1>
 *   6 — gate_event : list <channel-int> <"rising"|"falling">
 *   7 — spectrum   : list <32 floats>     (only when matching selected channel)
 *   8 — block      : <count-int>
 *   9 — clap       : list of 513 (512 floats + model-name string)
 *
 * Setting the selected spectrum channel:
 *   - From a [umenu] populated as ch1..ch14, wire its `int` outlet
 *     directly to inlet 1: the v8 will treat 0..13 as 0-based and
 *     internally add 1.
 *   - Alternatively send `set N` (1..14) for explicit 1-based input.
 */

autowatch = 1;     // re-load when the file changes on disk
inlets   = 2;
outlets  = 10;

setinletassist(0, "raw OSC from [udpreceive 9000]");
setinletassist(1, "selected spectrum channel (umenu int = 0-based, or set N = 1-based)");

setoutletassist(0, "rms       list <ch> <val>");
setoutletassist(1, "centroid  list <ch> <val>");
setoutletassist(2, "onset     list <ch> <env>");
setoutletassist(3, "cv        list <ch> <val>");
setoutletassist(4, "cv_rate   list <ch> <rate>");
setoutletassist(5, "gate      list <ch> <state>");
setoutletassist(6, "gate_event list <ch> <rising|falling>");
setoutletassist(7, "spectrum  list of 32 floats (selected channel only)");
setoutletassist(8, "block     <count>");
setoutletassist(9, "clap      list of 513 (512 floats + model name)");

const OUT_RMS        = 0;
const OUT_CENTROID   = 1;
const OUT_ONSET      = 2;
const OUT_CV         = 3;
const OUT_CV_RATE    = 4;
const OUT_GATE       = 5;
const OUT_GATE_EVENT = 6;
const OUT_SPECTRUM   = 7;
const OUT_BLOCK      = 8;
const OUT_CLAP       = 9;

// Map feature → outlet index for /synapse/<feat>/<ch> messages.
const FEATURE_OUTLET = {
    "rms":        OUT_RMS,
    "centroid":   OUT_CENTROID,
    "onset":      OUT_ONSET,
    "cv":         OUT_CV,
    "cv_rate":    OUT_CV_RATE,
    "gate":       OUT_GATE,
    "gate_event": OUT_GATE_EVENT,
    // spectrum handled specially below
};

// 1-based channel number that the user has currently selected for the
// spectrum display. Defaults to 1 so something is visible immediately
// without needing a click.
let selectedSpectrumCh = 1;

// `anything()` is called for any message whose selector didn't match a
// dedicated handler — every OSC message lands here because the address
// IS the selector.
function anything() {
    if (inlet !== 0) {
        return;
    }
    const addr = messagename;
    const args = arrayfromargs(arguments);

    // Single-segment leaves first (cheaper than the path parse below).
    if (addr === "/synapse/block") {
        // /synapse/block <int>
        outlet(OUT_BLOCK, args.length > 0 ? args[0] : 0);
        return;
    }
    if (addr === "/synapse/clap") {
        // /synapse/clap <512 floats> <model-name>
        outlet(OUT_CLAP, args);
        return;
    }

    // Per-channel feature: /synapse/<feat>/<ch>. Hand-parse to avoid
    // string allocations on every block (~70 bundles/s × ~30 messages).
    if (addr.charCodeAt(0) !== 47) return;  // '/'
    const idx2 = addr.indexOf("/", 1);
    if (idx2 < 0) return;
    const idx3 = addr.indexOf("/", idx2 + 1);
    if (idx3 < 0) return;
    if (addr.substring(1, idx2) !== "synapse") return;

    const feat = addr.substring(idx2 + 1, idx3);
    const ch = parseInt(addr.substring(idx3 + 1), 10);
    if (isNaN(ch)) return;

    if (feat === "spectrum") {
        if (ch === selectedSpectrumCh) {
            outlet(OUT_SPECTRUM, args);
        }
        return;
    }

    const out = FEATURE_OUTLET[feat];
    if (out === undefined) return;

    // Prepend channel so a downstream [route 1 2 ... 14] can demux.
    outlet(out, [ch].concat(args));
}

// Selected spectrum channel — int input on inlet 1.
// umenu output is 0-based (0..13 selecting items "ch1".."ch14"), so we
// add 1. If the value is already in [1, 14] it'll over-shift to [2, 15]
// which silently emits no spectrum — use the `set` message form below
// to bypass that for explicit 1-based input.
function msg_int(n) {
    if (inlet !== 1) return;
    selectedSpectrumCh = n + 1;
}

function msg_float(n) {
    msg_int(Math.round(n));
}

// Explicit 1-based input via `set N`.
function set(n) {
    if (inlet !== 1) return;
    selectedSpectrumCh = parseInt(n, 10);
}
