"""Prompt tests for the Helm agent."""

from __future__ import annotations

from pathlib import Path
import yaml

_AGENT_DIR = Path(__file__).parent.parent


def test_agent_yaml_exists() -> None:
    assert (_AGENT_DIR / "agent.yaml").exists()


def test_soul_md_exists() -> None:
    assert (_AGENT_DIR / "SOUL.md").exists()


def test_rules_md_exists() -> None:
    assert (_AGENT_DIR / "RULES.md").exists()


def test_coral_yaml_exists() -> None:
    assert (_AGENT_DIR / "tools" / "coral.yaml").exists()


def test_agent_yaml_schema() -> None:
    spec = yaml.safe_load((_AGENT_DIR / "agent.yaml").read_text())
    assert spec["name"] == "helm"
    assert spec["model"]["name"] == "claude-opus-4-6"
    assert spec["model"].get("effort") == "high"
    assert spec["runtime"]["flow_role"] == "specialist"


def test_coral_yaml_has_pagerduty() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    sources = coral["tools"][0]["restrictions"]["allowed_sources"]
    assert "pagerduty" in sources


def test_incident_summary_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "incident_summary.md").exists()


def test_risk_heatmap_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "risk_heatmap.md").exists()


def test_rules_mentions_confidence_levels() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    assert "confidence" in rules.lower()
    assert "high" in rules.lower()
