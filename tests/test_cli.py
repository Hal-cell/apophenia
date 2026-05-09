"""Tests for the CLI's read-only subcommands.

`run` is verified end-to-end via `conduit run` smoke calls (manual);
we don't unit-test it because it spawns the GLSL window which needs a
display. `devices` and `smoke` touch real audio hardware so are also
covered manually.

This module covers the deterministic subcommands:
  * `conduit version` — package + dep versions
  * `conduit config`  — resolved paths + default audio device
  * `--help`            — lists all public subcommands
"""

from __future__ import annotations

from typer.testing import CliRunner

from conduit.cli import app

runner = CliRunner()


def test_version_command_runs_and_mentions_conduit() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "conduit" in out
    assert "python" in out


def test_version_command_lists_key_packages() -> None:
    """Version output surfaces key deps so users can sanity-check
    their environment when filing a bug."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "numpy" in out
    assert "fastapi" in out
    assert "python-osc" in out


def test_config_command_runs_clean() -> None:
    """`config` should run without error and print the audio device row."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    # Phase 13: there's no preset state on disk anymore (autopilot is
    # deterministic from seed) — just verify it runs and mentions the
    # audio source.
    assert "audio" in out or "input" in out or "source" in out


def test_help_lists_all_subcommands() -> None:
    """Smoke test: the typer help output mentions every public subcommand."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    for cmd in ("run", "devices", "smoke", "version", "config"):
        assert cmd in out, f"--help missing '{cmd}'"
