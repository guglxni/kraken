"""Snapshot tests for voyage V4: Angry Whales."""

from __future__ import annotations

from kraken.voyages.compiler import compile_voyage, validate_voyage


def test_angry_whales_compiles() -> None:
    compiled = compile_voyage("angry_whales", {})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_angry_whales_required_sources() -> None:
    compiled = compile_voyage("angry_whales", {})
    sources = compiled.required_sources
    assert "stripe" in sources
    assert "sentry" in sources
    assert "intercom" in sources


def test_angry_whales_mrr_threshold_default() -> None:
    compiled = compile_voyage("angry_whales", {})
    assert compiled.params["mrr_threshold"] == 2000.0


def test_angry_whales_sql_contains_mrr_filter() -> None:
    compiled = compile_voyage("angry_whales", {"mrr_threshold": 5000})
    assert "5000" in compiled.sql


def test_angry_whales_sql_has_risk_score() -> None:
    compiled = compile_voyage("angry_whales", {})
    assert "risk" in compiled.sql.lower() or "churn" in compiled.sql.lower()


def test_angry_whales_validates() -> None:
    errors = validate_voyage("angry_whales")
    assert errors == [], f"Validation errors: {errors}"
