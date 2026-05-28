"""Tests for the KRAKEN CLI commands (no Coral connection required)."""

from __future__ import annotations

from click.testing import CliRunner

from kraken.cli import cli


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "voyage:run" in result.output
    assert "voyage:list" in result.output


def test_voyage_list() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["voyage:list"])
    assert result.exit_code == 0
    assert "exec_escalation" in result.output
    assert "hot_deploy" in result.output


def test_voyage_lint_all() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["voyage:lint"])
    assert result.exit_code == 0
    assert "✓" in result.output


def test_voyage_compile_hero() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["voyage:compile", "exec_escalation"])
    assert result.exit_code == 0
    assert "gmail" in result.output.lower()
    assert "SELECT" in result.output


def test_voyage_compile_unknown_fails() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["voyage:compile", "does_not_exist"])
    assert result.exit_code == 1
    assert "error" in result.output.lower() or "Error" in result.output


def test_voyage_run_dry_run() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["voyage:run", "hot_deploy", "--dry-run"])
    assert result.exit_code == 0
    assert "SELECT" in result.output
    assert "Sources" in result.output


def test_status_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Voyages" in result.output
    assert "Blackboard" in result.output
