"""Prompt tests for the Lookout agent."""

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
    assert spec["name"] == "lookout"
    assert spec["model"]["name"] == "claude-sonnet-4-6"
    assert spec["permission_mode"] == "plan"
    assert spec["runtime"]["flow_role"] == "specialist"


def test_coral_yaml_has_osv() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    sources = coral["tools"][0]["restrictions"]["allowed_sources"]
    assert "osv" in sources


def test_fresh_cve_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "fresh_cve.md").exists()


def test_stigmergic_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "stigmergic_self_ref.md").exists()


def test_cvss_scoring_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "cvss_scoring.md").exists()


def test_compliance_mapping_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "compliance_mapping.md").exists()


def test_rules_mentions_soc2() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    assert "SOC 2" in rules or "ISO 27001" in rules


def test_soul_mentions_cvss() -> None:
    soul = (_AGENT_DIR / "SOUL.md").read_text()
    assert "CVSS" in soul
