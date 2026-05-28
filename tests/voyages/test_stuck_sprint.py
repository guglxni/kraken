"""Snapshot tests for voyage V3: Stuck Sprint."""

from __future__ import annotations

import pytest

from kraken.voyages.compiler import VoyageCompileError, compile_voyage, validate_voyage


def test_stuck_sprint_compiles() -> None:
    compiled = compile_voyage("stuck_sprint", {"team_name": "Platform"})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_stuck_sprint_requires_team_name() -> None:
    with pytest.raises(VoyageCompileError, match="requires param"):
        compile_voyage("stuck_sprint", {})


def test_stuck_sprint_required_sources() -> None:
    compiled = compile_voyage("stuck_sprint", {"team_name": "Platform"})
    sources = compiled.required_sources
    assert "linear" in sources
    assert "github" in sources


def test_stuck_sprint_sql_contains_team() -> None:
    compiled = compile_voyage("stuck_sprint", {"team_name": "DataInfra"})
    assert "DataInfra" in compiled.sql


def test_stuck_sprint_stale_days_default() -> None:
    compiled = compile_voyage("stuck_sprint", {"team_name": "Eng"})
    assert compiled.params["stale_pr_days"] == 3


def test_stuck_sprint_sprint_id_default() -> None:
    compiled = compile_voyage("stuck_sprint", {"team_name": "Eng"})
    assert compiled.params["sprint_id"] == "current"


def test_stuck_sprint_validates() -> None:
    errors = validate_voyage("stuck_sprint")
    assert errors == [], f"Validation errors: {errors}"
