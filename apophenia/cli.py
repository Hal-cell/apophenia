"""apophenia CLI entry point.

Subcommands:
    run         spin up the audio capture thread + uvicorn server + render window
    devices     list available Core Audio input devices
    smoke       run the source for a few seconds and print frame stats
"""

from __future__ import annotations

import logging
import threading
import time
import webbrowser

import numpy as np
import typer
import uvicorn
from rich.console import Console

from apophenia.audio.features_fast import FeatureBus, fast_features_loop
from apophenia.audio.features_slow import (
    AudioBuffer,
    CLAP_WINDOW_SECONDS,
    SlowBus,
    slow_features_loop,
)
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
    render: bool = typer.Option(
        True,
        "--render/--no-render",
        help="Open the GLSL render window. --no-render keeps just audio + meter web UI.",
    ),
    clap: bool = typer.Option(
        True,
        "--clap/--no-clap",
        help="Run CLAP audio embedding at ~1Hz. First call downloads ~600MB. --no-clap skips it (no slow tier).",
    ),
) -> None:
    """Run audio capture + meter web UI + (optionally) the render window.

    Phase 3 default: audio thread + uvicorn (web meter) + GLSL render
    window all run together. Render window owns the main thread (Cocoa
    requires GUI on main); audio + uvicorn live in daemon threads.

    `--no-render` keeps the phase-1 behaviour: server runs on the main
    thread, no render window. Useful for headless dev or remote sessions.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    src = parse_source_arg(source)
    bus = FeatureBus()
    stop_event = threading.Event()

    # Slow tier (CLAP). Optional via --no-clap; the AudioBuffer is the
    # bridge from fast loop to slow worker. Buffer holds ~2s so the
    # slow worker can always read a fresh 1s window.
    slow_bus: SlowBus | None = None
    audio_buffer: AudioBuffer | None = None
    slow_thread: threading.Thread | None = None
    if clap:
        slow_bus = SlowBus()
        audio_buffer = AudioBuffer(
            n_channels=src.n_channels,
            sample_rate=src.sample_rate,
            duration_s=CLAP_WINDOW_SECONDS * 2,
        )
        slow_thread = threading.Thread(
            target=slow_features_loop,
            args=(src, audio_buffer, slow_bus, stop_event),
            name="audio_features_slow",
            daemon=True,
        )
        slow_thread.start()

    audio_thread = threading.Thread(
        target=fast_features_loop,
        args=(src, bus, stop_event, audio_buffer),
        name="audio_features_fast",
        daemon=True,
    )
    audio_thread.start()

    web_app = make_app(bus, slow_bus=slow_bus, broadcast_hz=broadcast_hz)
    url = f"http://127.0.0.1:{port}"

    console.print()
    console.print("[bold green]apophenia · phase 4 running[/bold green]")
    console.print(
        f"  source:  [cyan]{type(src).__name__}[/cyan]  "
        f"({src.n_channels}ch @ {src.sample_rate}Hz, block {src.block_size})"
    )
    console.print(f"  meter:   [cyan]{url}[/cyan]")
    console.print(f"  render:  {'[green]on[/green] (GLSL window)' if render else '[yellow]off[/yellow]'}")
    console.print(f"  clap:    {'[green]on[/green] (~1Hz)' if clap else '[yellow]off[/yellow]'}")
    console.print("  ws hz:   30")
    console.print("  ctrl-c (terminal) or close window to stop")
    console.print()

    if not no_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()

    if not render:
        # Phase-1 path: uvicorn on main thread, audio in background.
        try:
            uvicorn.run(web_app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
        finally:
            stop_event.set()
            audio_thread.join(timeout=1.0)
            if slow_thread is not None:
                slow_thread.join(timeout=2.0)
        return

    # --- render-on path (phase-3 default) ---
    # Run uvicorn in a daemon thread so the main thread can host the GL window.
    config = uvicorn.Config(
        web_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    def _serve() -> None:
        try:
            server.run()
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).exception("uvicorn died")

    server_thread = threading.Thread(target=_serve, name="uvicorn", daemon=True)
    server_thread.start()

    # Wait briefly for uvicorn to bind so the meter is responsive when
    # the user alt-tabs to the browser. 0.25s is plenty on macOS.
    time.sleep(0.25)

    # Import lazily — only the [visuals] extra ships moderngl-window /
    # glfw, so headless installs don't pay the import cost on `--no-render`.
    try:
        import moderngl_window as mglw
        from apophenia.visuals.shader_engine import ApopheniaWindow
    except ImportError as e:
        console.print(
            f"[red]render requested but visuals extras aren't installed:[/red] {e}"
        )
        console.print("[yellow]install with:[/yellow] uv sync --extra visuals")
        stop_event.set()
        server.should_exit = True
        return

    ApopheniaWindow.bus = bus

    # Bug workaround: moderngl_window's parse_args does
    # `args or sys.argv[1:]` (line 384, mglw 3.1.1), and an empty list
    # is falsy in Python, so passing `args=[]` to ask mglw to use only
    # WindowConfig defaults still ends up parsing user's CLI argv —
    # which contains typer's `run --source ... --no-browser` flags and
    # crashes argparse. Temporarily swap sys.argv to just the program
    # name so the fallback also yields an empty list.
    import sys

    saved_argv = sys.argv[:]
    sys.argv = sys.argv[:1]
    try:
        mglw.run_window_config(ApopheniaWindow, args=[])
    finally:
        sys.argv = saved_argv
        stop_event.set()
        server.should_exit = True
        audio_thread.join(timeout=1.0)
        if slow_thread is not None:
            slow_thread.join(timeout=2.0)
        server_thread.join(timeout=2.0)


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
    console.print("  [dim]idx   ch     sr        name[/dim]")
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
    """Pull frames from a source for N seconds and print per-channel RMS."""
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
