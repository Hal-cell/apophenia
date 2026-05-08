"""Tests for the CLI's read-only subcommands.

`run` is verified end-to-end via `apophenia run --no-render --no-clap
--no-ai` smoke calls (manual + the docs); we don't unit-test it because
it spawns daemon threads + a uvicorn server. `devices` and `smoke` are
also covered by manual tests since they touch real audio hardware.

This module covers the small, deterministic subcommands added in phase 8:
  * `apophenia version` — should mention the package + Python version
  * `apophenia config`  — should print the resolved preset path
"""

from __future__ import annotations

from typer.testing import CliRunner

from apophenia.cli import app

runner = CliRunner()


def test_version_command_runs_and_mentions_apophenia() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "apophenia" in out
    assert "python" in out


def test_version_command_lists_extra_packages() -> None:
    """Version output should surface key deps so users can sanity-check
    their environment when filing a bug."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "numpy" in out
    assert "fastapi" in out


def test_config_command_prints_preset_path() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout
    assert "presets" in out.lower()
    # The default preset path includes 'apophenia'.
    assert "apophenia" in out
    assert "presets.json" in out


def test_config_command_mentions_audio_source() -> None:
    """`config` should say something about the default audio device, even
    if it's "no input devices visible" — the user wants to know either
    way."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "audio" in out or "input" in out or "source" in out


def test_help_lists_all_subcommands() -> None:
    """Smoke test: the typer help output mentions every public subcommand."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    for cmd in ("run", "devices", "smoke", "version", "config"):
        assert cmd in out, f"--help missing '{cmd}'"
