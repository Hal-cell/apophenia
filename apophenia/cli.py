"""apophenia CLI entry point.

Subcommands:
    run         spin up the audio capture thread + control web server
    devices     list available Core Audio input devices
    smoke       run the source for a few seconds and print frame stats
"""

from __future__ import annotations

import threading
import time
import webbrowser

import numpy as np
import typer
import uvicorn
from rich.console import Console

from apophenia.audio.features_fast import FeatureBus, fast_features_loop
from apophenia.audio.source import parse_source_arg
from apophenia.control.server import make_app

app = typer.Typer(
    name="apophenia",
    help="Multi-channel audio-reactive AV instrument.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def run(
    source: str = typer.Option(
        "mock",
        "--source",
        "-s",
        help="Audio source spec: 'mock', 'mock:<pattern>', 'file:<path>', 'device:<name>'.",
    ),
    port: int = typer.Option(8000, "--port", "-p", help="HTTP / WebSocket port."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't auto-open the meter URL in your default browser."
    ),
    broadcast_hz: float = typer.Option(
        30.0, "--broadcast-hz", help="WebSocket fast-feature broadcast rate."
    ),
) -> None:
    """Run audio capture + level-meter web UI.

    Phase 1: pulls blocks from the chosen source, computes per-channel
    RMS + peak in a worker thread, broadcasts the latest snapshot to any
    WebSocket clients at `--broadcast-hz`. Visit the printed URL in a
    browser to see 14 vertical level bars.

    Audio engine and AI engine land in later phases — for now this is
    just the audio-input verification step.
    """
    src = parse_source_arg(source)
    bus = FeatureBus()
    stop_event = threading.Event()

    audio_thread = threading.Thread(
        target=fast_features_loop,
        args=(src, bus, stop_event),
        name="audio_features_fast",
        daemon=True,
    )
    audio_thread.start()

    web_app = make_app(bus, broadcast_hz=broadcast_hz)
    url = f"http://127.0.0.1:{port}"

    console.print()
    console.print("[bold green]apophenia · phase 2 running[/bold green]")
    console.print(f"  source:  [cyan]{type(src).__name__}[/cyan]  ({src.n_channels}ch @ {src.sample_rate}Hz, block {src.block_size})")
    console.print(f"  meter:   [cyan]{url}[/cyan]")
    console.print("  ws hz:   30")
    console.print("  ctrl-c to stop")
    console.print()

    if not no_browser:
        # Open the browser slightly after server start so the page doesn't
        # land on a connection-refused screen. uvicorn binds within ~50ms
        # but we wait 250ms to be safe across machines.
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run(web_app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    finally:
        stop_event.set()
        audio_thread.join(timeout=1.0)
        if audio_thread.is_alive():
            console.print("[yellow]warning: audio thread didn't shut down within 1s[/yellow]")


@app.command()
def devices() -> None:
    """List Core Audio input devices visible to the system.

    Devices we recognise as common multi-channel routes for apophenia
    (ES-9, BlackHole, Pro Tools Audio Bridge, Loopback) get a ★ marker.
    Pick any of them with `--source device:"<exact name>"`.
    """
    from apophenia.audio.device import list_devices

    devs = list_devices()
    if not devs:
        console.print("[red]no input devices found (or sounddevice unavailable).[/red]")
        raise typer.Exit(code=1)
    console.print("[bold]input devices:[/bold]")
    console.print(
        "  [dim]idx   ch     sr        name[/dim]"
    )
    interesting = ("ES-9", "BlackHole", "Pro Tools Audio Bridge", "Loopback")
    for d in devs:
        is_multi = d["max_input_channels"] >= 14
        marker = " ★" if any(s in d["name"] for s in interesting) and is_multi else ""
        console.print(
            f"  {d['index']:>3}  {d['max_input_channels']:>3}   "
            f"{d['default_samplerate']:>6}Hz   {d['name']}{marker}"
        )
    console.print()
    console.print(
        "[dim]use:[/dim] [cyan]apophenia run --source device:\"<exact name>\"[/cyan]"
    )


@app.command()
def smoke(
    source: str = typer.Option("mock:drums", "--source", "-s"),
    seconds: float = typer.Option(3.0, "--seconds", "-t"),
) -> None:
    """Pull frames from a source for N seconds and print per-channel RMS.

    Quick-and-dirty sanity check the source is producing real data at
    real-time pace. Phase 0 ships this so we can verify Mock works
    end-to-end before any feature extraction lands.
    """
    src = parse_source_arg(source)
    src.open()
    try:
        n_blocks = int(seconds * src.sample_rate / src.block_size)
        rms_acc = np.zeros(src.n_channels, dtype=np.float64)
        peak = np.zeros(src.n_channels, dtype=np.float64)
        actual_blocks = 0
        t0 = time.monotonic()

        for block in src.frames():
            actual_blocks += 1
            rms_acc += np.sqrt(np.mean(block.astype(np.float64) ** 2, axis=1))
            peak = np.maximum(peak, np.max(np.abs(block), axis=1))
            if actual_blocks >= n_blocks:
                break

        elapsed = time.monotonic() - t0
        rms_avg = rms_acc / actual_blocks

        console.print(f"\n[bold]captured {actual_blocks} blocks in {elapsed:.2f}s[/bold]")
        expected = n_blocks * src.block_size / src.sample_rate
        console.print(f"  expected ~{expected:.2f}s (real-time pacing)")

        console.print("\n[bold]per-channel summary:[/bold]")
        console.print("  ch  avg_rms  peak    bar")
        for ch in range(src.n_channels):
            r = rms_avg[ch]
            p = peak[ch]
            # Quick visual bar (RMS scale, max 0.5 → full bar of 30 chars).
            bar_len = int(min(r / 0.5, 1.0) * 30)
            bar = "█" * bar_len + "·" * (30 - bar_len)
            console.print(f"  {ch + 1:>2}  {r:6.4f}  {p:5.3f}  {bar}")
    finally:
        src.close()


def main() -> None:
    """Entry point referenced by [project.scripts] in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
