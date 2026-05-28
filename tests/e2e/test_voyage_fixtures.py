"""Fixture-based e2e tests — verify voyage output schema matches expectations.

These tests do NOT require a live Coral connection. They validate that:
1. Each voyage compiles without error
2. The fixture data matches the voyage's declared output_schema
3. The demo narrative (Acme story) is internally consistent across voyages

Run: uv run pytest tests/e2e/ -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
VOYAGES_DIR = Path(__file__).parent.parent.parent / "kraken" / "voyages"

FIXTURE_FILES = {
    "exec_escalation": FIXTURES_DIR / "exec_escalation_result.json",
    "hot_deploy": FIXTURES_DIR / "hot_deploy_result.json",
    "incident_summary": FIXTURES_DIR / "incident_summary_result.json",
    "angry_whales": FIXTURES_DIR / "angry_whales_result.json",
    "fresh_cve": FIXTURES_DIR / "fresh_cve_result.json",
}


def _load_fixture(voyage_name: str) -> dict:
    path = FIXTURE_FILES[voyage_name]
    assert path.exists(), f"Fixture missing: {path}"
    return json.loads(path.read_text())


def _load_voyage_spec(voyage_name: str) -> dict:
    path = VOYAGES_DIR / f"{voyage_name}.yaml"
    assert path.exists(), f"Voyage spec missing: {path}"
    return yaml.safe_load(path.read_text())


# ── Fixture schema validation ─────────────────────────────────────────────────

@pytest.mark.parametrize("voyage_name", list(FIXTURE_FILES.keys()))
def test_fixture_has_required_fields(voyage_name: str) -> None:
    fixture = _load_fixture(voyage_name)
    assert "voyage" in fixture
    assert "rows" in fixture
    assert "row_count" in fixture
    assert "sources_queried" in fixture
    assert fixture["voyage"] == voyage_name


@pytest.mark.parametrize("voyage_name", list(FIXTURE_FILES.keys()))
def test_fixture_row_count_matches_rows(voyage_name: str) -> None:
    fixture = _load_fixture(voyage_name)
    assert fixture["row_count"] == len(fixture["rows"])


@pytest.mark.parametrize("voyage_name", list(FIXTURE_FILES.keys()))
def test_fixture_sources_match_voyage_spec(voyage_name: str) -> None:
    fixture = _load_fixture(voyage_name)
    spec = _load_voyage_spec(voyage_name)
    required = set(spec.get("required_sources", []))
    queried = set(fixture.get("sources_queried", []))
    assert queried.issubset(required | {"local_codebase", "local-codebase"}), (
        f"{voyage_name}: queried sources {queried} not subset of required {required}"
    )


@pytest.mark.parametrize("voyage_name", list(FIXTURE_FILES.keys()))
def test_fixture_output_schema_columns_present(voyage_name: str) -> None:
    """Verify fixture rows have columns declared in output_schema."""
    fixture = _load_fixture(voyage_name)
    spec = _load_voyage_spec(voyage_name)
    output_schema = spec.get("output_schema", [])
    if not output_schema or not fixture["rows"]:
        return
    expected_columns = {col["name"] for col in output_schema}
    actual_columns = set(fixture["rows"][0].keys())
    missing = expected_columns - actual_columns
    assert not missing, (
        f"{voyage_name}: output_schema columns missing from fixture: {missing}"
    )


# ── Demo narrative consistency (Acme story) ───────────────────────────────────

def test_demo_narrative_acme_appears_in_exec_escalation() -> None:
    """The hero voyage fixture must reference Acme as the escalating customer."""
    fixture = _load_fixture("exec_escalation")
    rows = fixture["rows"]
    assert len(rows) >= 1
    row = rows[0]
    assert "acme" in row.get("customer", "").lower() or "acme" in row.get("from", "").lower()


def test_demo_narrative_same_deploy_sha_in_hot_deploy_and_incident() -> None:
    """The suspect deploy SHA should be consistent across hot_deploy and incident_summary."""
    hot = _load_fixture("hot_deploy")["rows"][0]
    incident = _load_fixture("incident_summary")["rows"][0]
    assert hot["deploy_sha"] == incident["suspect_deploy_sha"], (
        "Demo narrative broken: deploy SHA differs between hot_deploy and incident_summary"
    )


def test_demo_narrative_same_pr_author_in_incident() -> None:
    """The PR author in incident_summary must match hot_deploy."""
    hot = _load_fixture("hot_deploy")["rows"][0]
    incident = _load_fixture("incident_summary")["rows"][0]
    assert hot["pr_author"] == incident["pr_author"], (
        "Demo narrative broken: PR author differs between hot_deploy and incident_summary"
    )


def test_demo_narrative_acme_top_whale() -> None:
    """Acme must be the highest-risk whale in angry_whales fixture."""
    fixture = _load_fixture("angry_whales")
    rows = fixture["rows"]
    assert len(rows) >= 1
    top = rows[0]  # sorted by churn_risk_score DESC
    assert top["churn_risk_score"] >= 90.0, f"Top whale risk score too low: {top['churn_risk_score']}"
    assert top["mrr"] >= 10000.0, f"Top whale MRR too low: {top['mrr']}"


def test_demo_narrative_exec_escalation_has_errors() -> None:
    """The hero voyage fixture must show active errors above threshold."""
    fixture = _load_fixture("exec_escalation")
    row = fixture["rows"][0]
    assert row["active_errors"] > 100, "Demo: hero voyage should show significant error spike"
    assert row["current_p99"] > 1000.0, "Demo: hero voyage should show latency degradation"


def test_demo_narrative_cve_high_severity() -> None:
    """The fresh_cve fixture must have a critical-severity CVE."""
    fixture = _load_fixture("fresh_cve")
    row = fixture["rows"][0]
    assert row["severity_score"] >= 7.0, "Demo CVE should be high or critical severity"


# ── Latency targets ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("voyage_name,max_ms", [
    ("exec_escalation", 30000),  # ARCHITECTURE.md target: <30s
    ("hot_deploy", 30000),
    ("incident_summary", 30000),
    ("angry_whales", 30000),
    ("fresh_cve", 30000),
])
def test_fixture_latency_within_target(voyage_name: str, max_ms: float) -> None:
    fixture = _load_fixture(voyage_name)
    assert fixture["latency_ms"] <= max_ms, (
        f"{voyage_name}: fixture latency {fixture['latency_ms']}ms exceeds {max_ms}ms target"
    )
