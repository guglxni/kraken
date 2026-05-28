"""Snapshot tests for voyage V6: Executive Escalation (HERO VOYAGE).

This is the primary demo voyage. These tests must pass on every commit.
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from kraken.voyages.compiler import compile_voyage, validate_voyage

_YAML_PATH = Path(__file__).parent.parent.parent / "kraken" / "voyages" / "exec_escalation.yaml"
_J2_PATH = Path(__file__).parent.parent.parent / "kraken" / "voyages" / "exec_escalation.sql.j2"


def test_exec_escalation_yaml_exists() -> None:
    assert _YAML_PATH.exists(), "exec_escalation.yaml must exist"


def test_exec_escalation_j2_exists() -> None:
    assert _J2_PATH.exists(), (
        "exec_escalation.sql.j2 must exist — hero voyage uses external SQL template"
    )


def test_exec_escalation_compiles_with_defaults() -> None:
    compiled = compile_voyage("exec_escalation", {})
    assert compiled.sql is not None
    assert len(compiled.sql) > 200, "Hero voyage SQL is suspiciously short"
    assert "SELECT" in compiled.sql.upper()
    assert "FROM" in compiled.sql.upper()
    assert "LIMIT" in compiled.sql.upper()


def test_exec_escalation_required_sources_count() -> None:
    """Hero voyage must touch all 8 declared sources."""
    compiled = compile_voyage("exec_escalation", {})
    assert len(compiled.required_sources) == 8, (
        f"Expected 8 sources, got {len(compiled.required_sources)}: "
        f"{compiled.required_sources}"
    )


def test_exec_escalation_required_sources_content() -> None:
    compiled = compile_voyage("exec_escalation", {})
    required = set(compiled.required_sources)
    expected = {"gmail", "intercom", "stripe", "sentry", "datadog", "github", "pagerduty", "osv"}
    assert required == expected, f"Source mismatch: {required} != {expected}"


def test_exec_escalation_sql_joins_all_sources() -> None:
    compiled = compile_voyage("exec_escalation", {})
    sql_lower = compiled.sql.lower()
    for source in ["gmail", "intercom", "stripe", "sentry", "datadog", "github", "osv"]:
        assert source in sql_lower, f"Hero voyage SQL missing source: {source}"


def test_exec_escalation_default_params() -> None:
    compiled = compile_voyage("exec_escalation", {})
    assert compiled.params["hours_back"] == 6
    assert compiled.params["mrr_threshold"] == 10000


def test_exec_escalation_custom_params() -> None:
    compiled = compile_voyage("exec_escalation", {"hours_back": 24, "mrr_threshold": 50000})
    assert "24" in compiled.sql
    assert "50000" in compiled.sql


def test_exec_escalation_no_select_star() -> None:
    compiled = compile_voyage("exec_escalation", {})
    for line in compiled.sql.splitlines():
        assert "SELECT *" not in line.upper(), f"Found SELECT * in hero voyage: {line}"


def test_exec_escalation_output_schema_complete() -> None:
    compiled = compile_voyage("exec_escalation", {})
    schema_names = [col["name"] for col in compiled.output_schema]
    expected_cols = [
        "subject", "from", "snippet", "customer", "mrr",
        "active_errors", "current_p99", "last_deploy", "deployed_at",
        "open_incidents", "unpatched_cves",
    ]
    for col in expected_cols:
        assert col in schema_names, (
            f"Hero voyage output_schema missing column: {col}"
        )


def test_exec_escalation_uses_external_j2() -> None:
    spec = yaml.safe_load(_YAML_PATH.read_text())
    assert spec["sql"].endswith(".j2"), (
        "exec_escalation must reference an external .sql.j2 file"
    )


def test_exec_escalation_validates() -> None:
    errors = validate_voyage("exec_escalation")
    assert errors == [], f"Hero voyage has validation errors: {errors}"


def test_exec_escalation_version_is_1_1() -> None:
    """Hero voyage should be at version 1.1.0 (upgraded from 1.0.0 in phase 1.5)."""
    spec = yaml.safe_load(_YAML_PATH.read_text())
    assert spec["version"] == "1.1.0"
