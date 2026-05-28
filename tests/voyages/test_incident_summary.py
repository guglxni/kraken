"""Snapshot tests for voyage V2: Incident Auto-Summary."""

from __future__ import annotations

import pytest

from kraken.voyages.compiler import VoyageCompileError, compile_voyage, validate_voyage


def test_incident_summary_compiles() -> None:
    compiled = compile_voyage("incident_summary", {"incident_id": "INC-4821"})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_incident_summary_requires_incident_id() -> None:
    with pytest.raises(VoyageCompileError, match="requires param"):
        compile_voyage("incident_summary", {})


def test_incident_summary_required_sources() -> None:
    compiled = compile_voyage("incident_summary", {"incident_id": "INC-4821"})
    sources = compiled.required_sources
    assert "sentry" in sources
    assert "github" in sources
    assert "datadog" in sources


def test_incident_summary_sql_contains_incident_id() -> None:
    compiled = compile_voyage("incident_summary", {"incident_id": "INC-TEST-001"})
    assert "INC-TEST-001" in compiled.sql


def test_incident_summary_lookback_default() -> None:
    compiled = compile_voyage("incident_summary", {"incident_id": "INC-001"})
    assert compiled.params["lookback_hours"] == 4


def test_incident_summary_validates() -> None:
    errors = validate_voyage("incident_summary")
    assert errors == [], f"Validation errors: {errors}"
