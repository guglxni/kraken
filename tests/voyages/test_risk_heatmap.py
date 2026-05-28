"""Snapshot tests for voyage V7: Risk Heatmap."""

from __future__ import annotations

from kraken.voyages.compiler import compile_voyage, validate_voyage


def test_risk_heatmap_compiles() -> None:
    compiled = compile_voyage("risk_heatmap", {})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_risk_heatmap_required_sources() -> None:
    compiled = compile_voyage("risk_heatmap", {})
    sources = compiled.required_sources
    assert "github" in sources
    assert "sentry" in sources
    assert "osv" in sources


def test_risk_heatmap_top_n_default() -> None:
    compiled = compile_voyage("risk_heatmap", {})
    assert compiled.params["top_n"] == 15


def test_risk_heatmap_sql_contains_limit() -> None:
    compiled = compile_voyage("risk_heatmap", {"top_n": 25})
    assert "25" in compiled.sql


def test_risk_heatmap_sql_contains_union() -> None:
    """Risk heatmap aggregates multiple risk categories via UNION ALL."""
    compiled = compile_voyage("risk_heatmap", {})
    assert "UNION ALL" in compiled.sql.upper()


def test_risk_heatmap_validates() -> None:
    errors = validate_voyage("risk_heatmap")
    assert errors == [], f"Validation errors: {errors}"
