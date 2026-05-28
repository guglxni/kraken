"""Snapshot tests for voyage V8: Stigmergic Self-Reference.

This voyage is the architectural showpiece — it JOINs kraken.findings with
live sources to detect CVEs that were previously flagged but are still in prod.
"""

from __future__ import annotations

from kraken.voyages.compiler import compile_voyage, validate_voyage


def test_stigmergic_self_ref_compiles() -> None:
    compiled = compile_voyage("stigmergic_self_ref", {})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_stigmergic_self_ref_required_sources() -> None:
    compiled = compile_voyage("stigmergic_self_ref", {})
    sources = compiled.required_sources
    # Must include the blackboard — that is the self-referential part
    assert any("kraken" in s.lower() for s in sources), (
        "V8 must reference kraken.findings or kraken.plans as a source"
    )
    assert "github" in sources


def test_stigmergic_self_ref_default_params() -> None:
    compiled = compile_voyage("stigmergic_self_ref", {})
    assert compiled.params["lookback_days"] == 30


def test_stigmergic_self_ref_sql_self_references() -> None:
    """SQL must read from the kraken findings/plans tables (self-reference)."""
    compiled = compile_voyage("stigmergic_self_ref", {})
    sql_lower = compiled.sql.lower()
    assert "kraken" in sql_lower, (
        "V8 SQL must reference kraken.findings or kraken_findings — "
        "that is the whole point of this voyage"
    )


def test_stigmergic_self_ref_validates() -> None:
    errors = validate_voyage("stigmergic_self_ref")
    assert errors == [], f"Validation errors: {errors}"
