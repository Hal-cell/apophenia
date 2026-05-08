"""apophenia CLI entry point.

Subcommands:
    run         spin up the audio + control + render processes
    devices     list available Core Audio input devices
    smoke       run the source for a few seconds and print frame stats

In phase 0 only `devices` and `smoke` are wired. `run` lands in phase 1+
once the level-meter UI exists.
"""

from __future__ import annotations

import time

import numpy as np
import typer
from rich.console import Console

from apophenia.audio.source import AudioSource, parse_source_arg

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
) -> None:
    """Run the full audio + control + render pipeline.

    Phase 0 stub — currently just constructs the source and prints its
    metadata. Real run-loop lands in phase 1.
    """
    src = parse_source_arg(source)
    console.print(f"[green]source resolved:[/green] {type(src).__name__}")
    console.print(f"  channels={src.n_channels}  sr={src.sample_rate}  block={src.block_size}")
    console.print("[yellow]run loop is a phase-1 stub. use `apophenia smoke` to test the source.[/yellow]")


@app.command()
def devices() -> None:
    """List Core Audio input devices visible to the system."""
    from apophenia.audio.device import list_devices

    names = list_devices()
    if not names:
        console.print("[red]no input devices found (or sounddevice unavailable).[/red]")
        raise typer.Exit(code=1)
    console.print("[bold]input devices:[/bold]")
    for name in names:
        console.print(f"  • {name}")


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
