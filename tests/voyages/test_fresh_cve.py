"""Snapshot tests for voyage V5: Fresh CVE in Production."""

from __future__ import annotations

import pytest

from kraken.voyages.compiler import VoyageCompileError, compile_voyage, validate_voyage


def test_fresh_cve_compiles() -> None:
    compiled = compile_voyage("fresh_cve", {"cve_id": "CVE-2024-45490"})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_fresh_cve_requires_cve_id() -> None:
    with pytest.raises(VoyageCompileError, match="requires param"):
        compile_voyage("fresh_cve", {})


def test_fresh_cve_required_sources() -> None:
    compiled = compile_voyage("fresh_cve", {"cve_id": "CVE-2024-12345"})
    sources = compiled.required_sources
    assert "osv" in sources
    assert "github" in sources


def test_fresh_cve_sql_contains_cve_id() -> None:
    compiled = compile_voyage("fresh_cve", {"cve_id": "CVE-2024-TEST"})
    assert "CVE-2024-TEST" in compiled.sql


def test_fresh_cve_ecosystem_default() -> None:
    compiled = compile_voyage("fresh_cve", {"cve_id": "CVE-2024-12345"})
    assert compiled.params["ecosystem"] == "PyPI"


def test_fresh_cve_lookback_default() -> None:
    compiled = compile_voyage("fresh_cve", {"cve_id": "CVE-2024-12345"})
    assert compiled.params["lookback_days"] == 90


def test_fresh_cve_validates() -> None:
    errors = validate_voyage("fresh_cve")
    assert errors == [], f"Validation errors: {errors}"
