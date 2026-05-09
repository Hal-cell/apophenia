"""synapse CLI entry point.

Subcommands:
    run         spin up audio capture + meter web UI
    devices     list available Core Audio input devices
    smoke       run the source for a few seconds and print frame stats
    version     print package + dep versions
    config      print resolved paths

Phase-16 pivot: this used to be an audio-reactive AV instrument.
Going forward it's a multichannel audio analyser that extracts
CV / gate / spectrum from each input channel and forwards the
data to MaxMSP (or any OSC consumer) for further routing into
Unreal / external systems. The web UI is purely a viewer for
debugging audio.
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

from synapse.analysis import CVDetector, GateDetector
from synapse.audio.features_fast import FeatureBus, fast_features_loop
from synapse.audio.features_slow import (
    CLAP_WINDOW_SECONDS,
    AudioBuffer,
    SlowBus,
    slow_features_loop,
)
from synapse.audio.source import parse_source_arg
from synapse.channels import ChannelMap, ChannelRole
from synapse.control.server import make_app
from synapse.osc import OSCSender

app = typer.Typer(
    name="synapse",
    help="Multichannel audio analyser → MaxMSP bridge.",
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
        30.0, "--broadcast-hz", help="WebSocket meter broadcast rate."
    ),
    clap: bool = typer.Option(
        True,
        "--clap/--no-clap",
        help="Run CLAP audio embedding at ~1Hz. First call downloads ~600MB.",
    ),
    gate_channels: str = typer.Option(
        "",
        "--gate",
        help="Channels carrying Eurorack gate / trigger signals. Range syntax: '1,2,5-8'. "
             "These get Schmitt-trigger detection + edge events on OSC.",
    ),
    cv_channels: str = typer.Option(
        "",
        "--cv",
        help="Channels carrying Eurorack control voltage. Range syntax: '3-6'. "
             "These get IIR-low-pass DC value + rate-of-change on OSC.",
    ),
    audio_channels: str = typer.Option(
        "",
        "--audio",
        help="Channels carrying audio (default for unassigned channels). "
             "Range syntax: '7-14'. These get full RMS / centroid / onset analysis.",
    ),
    osc_host: str = typer.Option(
        "127.0.0.1",
        "--osc-host",
        help="OSC destination host. Defaults to localhost (Max on the same machine).",
    ),
    osc_port: int = typer.Option(
        9000, "--osc-port", help="OSC destination UDP port."
    ),
    no_osc: bool = typer.Option(
        False, "--no-osc", help="Disable OSC output (web meter only)."
    ),
) -> None:
    """Run audio capture + meter web UI.

    Audio runs in a daemon thread; the optional CLAP slow tier in a
    second daemon thread; the FastAPI / uvicorn server in the main
    thread (it's the only thing that needs to block).
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    src = parse_source_arg(source)
    bus = FeatureBus()
    stop_event = threading.Event()

    # ---- Channel role map (which channels are gates / cvs / audio). ---- #
    # Defaults: any channel not in --gate / --cv / --audio is audio.
    channel_map = ChannelMap.from_cli(
        n_channels=src.n_channels,
        gate=gate_channels or None,
        cv=cv_channels or None,
        audio=audio_channels or None,
    )

    # ---- Detectors ---- #
    # Audio block rate (block_size samples at the source's sample_rate).
    # CV detector + gate detector both run at this rate.
    block_rate = src.sample_rate / src.block_size
    cv_idx = channel_map.channels_with(ChannelRole.CV)
    gate_idx = channel_map.channels_with(ChannelRole.GATE)
    cv_detector = CVDetector(cv_idx, block_rate_hz=block_rate) if cv_idx else None
    gate_detector = GateDetector(gate_idx) if gate_idx else None

    # ---- OSC sender ---- #
    osc_sender = None if no_osc else OSCSender(host=osc_host, port=osc_port)

    # Slow tier (CLAP). Optional. Doesn't drive any output yet, but the
    # bus is wired so future OSC streams can carry mood / embedding.
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
        kwargs={
            "cv_detector": cv_detector,
            "gate_detector": gate_detector,
            "osc_sender": osc_sender,
        },
        name="audio_features_fast",
        daemon=True,
    )
    audio_thread.start()

    web_app = make_app(bus, slow_bus=slow_bus, broadcast_hz=broadcast_hz)
    url = f"http://127.0.0.1:{port}"

    # 1-based channel display for the banner (matches jack labels).
    def _ch_summary(role: ChannelRole) -> str:
        chs = channel_map.channels_with(role)
        if not chs:
            return "[dim]—[/dim]"
        return ",".join(str(i + 1) for i in chs)

    console.print()
    console.print("[bold green]synapse · running[/bold green]")
    console.print(
        f"  source:  [cyan]{type(src).__name__}[/cyan]  "
        f"({src.n_channels}ch @ {src.sample_rate}Hz, block {src.block_size})"
    )
    console.print(f"  audio:   [cyan]{_ch_summary(ChannelRole.AUDIO)}[/cyan]")
    console.print(f"  cv:      [cyan]{_ch_summary(ChannelRole.CV)}[/cyan]")
    console.print(f"  gate:    [cyan]{_ch_summary(ChannelRole.GATE)}[/cyan]")
    console.print(f"  meter:   [cyan]{url}[/cyan]")
    if osc_sender is not None:
        console.print(f"  osc:     [cyan]{osc_host}:{osc_port}[/cyan] (bundles per audio block)")
    else:
        console.print("  osc:     [yellow]off[/yellow]")
    console.print(f"  clap:    {'[green]on[/green] (~1Hz)' if clap else '[yellow]off[/yellow]'}")
    console.print("  ctrl-c to stop")
    console.print()

    if not no_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run(web_app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    finally:
        stop_event.set()
        audio_thread.join(timeout=1.0)
        if slow_thread is not None:
            slow_thread.join(timeout=2.0)


@app.command()
def devices() -> None:
    """List Core Audio input devices visible to the system."""
    from synapse.audio.device import list_devices

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
        "[dim]use:[/dim] [cyan]synapse run --source device:\"<exact name>\"[/cyan]"
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


@app.command()
def version() -> None:
    """Print synapse + key dep versions and the active Python interpreter."""
    import importlib.metadata as md
    import platform
    import sys

    try:
        ver = md.version("synapse")
    except md.PackageNotFoundError:
        ver = "unknown (not installed)"

    console.print(f"[bold]synapse[/bold] {ver}")
    console.print(f"  python:      {platform.python_version()} ({sys.executable})")
    console.print(f"  platform:    {platform.system()} {platform.machine()}")

    def _pkg(name: str) -> str:
        try:
            return md.version(name)
        except md.PackageNotFoundError:
            return "[dim]not installed[/dim]"

    console.print(f"  numpy:       {_pkg('numpy')}")
    console.print(f"  fastapi:     {_pkg('fastapi')}")
    console.print(f"  sounddevice: {_pkg('sounddevice')}")
    console.print(f"  python-osc:  {_pkg('python-osc')}")
    console.print(f"  torch:       {_pkg('torch')}    (clap extra)")
    console.print(f"  transformers:{_pkg('transformers')}    (clap extra)")


@app.command()
def config() -> None:
    """Print resolved paths + default audio device."""
    console.print("[bold]synapse · resolved paths[/bold]")
    console.print("  [dim](no persistent state — analyser is stateless across launches)[/dim]")

    console.print()
    console.print("[bold]default audio source:[/bold]")
    try:
        from synapse.audio.device import list_devices

        devs = list_devices()
        if not devs:
            console.print("  [red]no input devices visible[/red]")
        else:
            primary = devs[0]
            console.print(
                f"  [cyan]{primary['name']}[/cyan]  "
                f"({primary['max_input_channels']}ch @ "
                f"{primary['default_samplerate']:.0f}Hz, idx {primary['index']})"
            )
            console.print(
                "  [dim]list all with: synapse devices[/dim]"
            )
    except Exception as e:  # noqa: BLE001
        console.print(f"  [red]sounddevice unavailable:[/red] {e}")


def main() -> None:
    """Entry point referenced by [project.scripts] in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
