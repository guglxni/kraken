"""Tests for voyage compilation and SQL rendering.

These are snapshot tests — they verify that each voyage YAML compiles to valid SQL
without errors and that the SQL meets quality standards (no SELECT *, has LIMIT,
touches >= 3 sources). No Coral connection is required.
"""

from __future__ import annotations

import pytest

from kraken.voyages.compiler import (
    VoyageCompileError,
    compile_voyage,
    list_voyages,
    validate_voyage,
)


VOYAGE_NAMES = [
    "exec_escalation",
    "hot_deploy",
    "incident_summary",
    "stuck_sprint",
    "angry_whales",
    "fresh_cve",
    "risk_heatmap",
    "stigmergic_self_ref",
]

# Minimum params needed to compile each voyage (all others have defaults)
VOYAGE_PARAMS: dict[str, dict] = {
    # exec_escalation v1.1: all params have defaults (hours_back=6, mrr_threshold=10000)
    "exec_escalation": {},
    # hot_deploy: deploy_sha defaults to 'latest'
    "hot_deploy": {},
    # incident_summary: incident_id is required, no default
    "incident_summary": {"incident_id": "INC-001"},
    # stuck_sprint: team_name is required, no default
    "stuck_sprint": {"team_name": "Platform"},
    "angry_whales": {},
    # fresh_cve: cve_id is required, no default
    "fresh_cve": {"cve_id": "CVE-2024-12345"},
    "risk_heatmap": {},
    "stigmergic_self_ref": {},
}


def test_list_voyages_returns_all() -> None:
    voyages = list_voyages()
    names = [v["name"] for v in voyages]
    for expected in VOYAGE_NAMES:
        assert expected in names, f"Missing voyage: {expected}"


@pytest.mark.parametrize("voyage_name", VOYAGE_NAMES)
def test_voyage_compiles_without_error(voyage_name: str) -> None:
    params = VOYAGE_PARAMS.get(voyage_name, {})
    compiled = compile_voyage(voyage_name, params)
    assert compiled.name == voyage_name
    assert len(compiled.sql) > 100, "SQL too short — likely not rendered"
    assert "SELECT" in compiled.sql.upper()
    assert "FROM" in compiled.sql.upper()


@pytest.mark.parametrize("voyage_name", VOYAGE_NAMES)
def test_voyage_sql_has_limit(voyage_name: str) -> None:
    params = VOYAGE_PARAMS.get(voyage_name, {})
    compiled = compile_voyage(voyage_name, params)
    assert "LIMIT" in compiled.sql.upper(), f"{voyage_name}: missing LIMIT clause"


@pytest.mark.parametrize("voyage_name", VOYAGE_NAMES)
def test_voyage_sql_no_select_star(voyage_name: str) -> None:
    params = VOYAGE_PARAMS.get(voyage_name, {})
    compiled = compile_voyage(voyage_name, params)
    lines = [line.strip().upper() for line in compiled.sql.splitlines()]
    for line in lines:
        assert not line.startswith("SELECT *"), f"{voyage_name}: found SELECT *"


@pytest.mark.parametrize("voyage_name", VOYAGE_NAMES)
def test_voyage_requires_at_least_3_sources(voyage_name: str) -> None:
    params = VOYAGE_PARAMS.get(voyage_name, {})
    compiled = compile_voyage(voyage_name, params)
    assert len(compiled.required_sources) >= 3, (
        f"{voyage_name}: only {len(compiled.required_sources)} sources, need ≥ 3"
    )


def test_unknown_voyage_raises() -> None:
    with pytest.raises(VoyageCompileError, match="Unknown voyage"):
        compile_voyage("does_not_exist", {})


def test_missing_required_param_raises() -> None:
    # incident_summary requires incident_id with no default
    with pytest.raises(VoyageCompileError, match="requires param"):
        compile_voyage("incident_summary", {})


@pytest.mark.parametrize("voyage_name", VOYAGE_NAMES)
def test_voyage_validates_cleanly(voyage_name: str) -> None:
    errors = validate_voyage(voyage_name)
    assert errors == [], f"{voyage_name} has validation errors: {errors}"


def test_exec_escalation_param_substitution() -> None:
    """Hero voyage: verify Jinja2 renders hours_back and mrr_threshold."""
    compiled = compile_voyage(
        "exec_escalation",
        {"hours_back": 12, "mrr_threshold": 50000},
    )
    # Jinja rendered hours_back and mrr_threshold into the SQL
    assert "12" in compiled.sql
    assert "50000" in compiled.sql
    # Must reference all 8 hero sources
    assert "gmail" in compiled.sql.lower()
    assert "stripe" in compiled.sql.lower()
    assert "sentry" in compiled.sql.lower()
    assert "osv" in compiled.sql.lower()


def test_exec_escalation_default_params() -> None:
    """Hero voyage compiles cleanly with no params (uses defaults)."""
    compiled = compile_voyage("exec_escalation", {})
    assert compiled.params["hours_back"] == 6
    assert compiled.params["mrr_threshold"] == 10000
    assert len(compiled.required_sources) == 8


def test_hot_deploy_latest_default() -> None:
    compiled = compile_voyage("hot_deploy", {})
    # deploy_sha defaults to 'latest'
    assert "'latest'" in compiled.sql or "latest" in compiled.sql


def test_exec_escalation_is_external_j2() -> None:
    """Hero voyage uses external .sql.j2 template, not inline SQL."""
    import yaml
    from pathlib import Path
    spec = yaml.safe_load(
        (Path(__file__).parent.parent.parent / "kraken" / "voyages" / "exec_escalation.yaml")
        .read_text()
    )
    assert spec["sql"].endswith(".j2"), (
        "exec_escalation must use an external .sql.j2 file for the hero demo"
    )
