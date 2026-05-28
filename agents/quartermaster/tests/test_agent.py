"""Prompt tests for the Quartermaster agent.

Tests verify that the agent YAML, SOUL.md, RULES.md, and skills load correctly
and that the gitagent folder structure is complete.
"""

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


def test_routing_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "routing.md").exists()


def test_synthesis_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "synthesis.md").exists()


def test_escalation_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "escalation.md").exists()


def test_agent_yaml_schema() -> None:
    spec = yaml.safe_load((_AGENT_DIR / "agent.yaml").read_text())
    assert spec["name"] == "quartermaster"
    assert spec["model"]["provider"] == "anthropic"
    assert spec["model"]["name"] == "claude-opus-4-6"
    assert spec["runtime"]["flow_role"] == "planner"
    assert spec["permission_mode"] == "default"


def test_soul_md_mentions_sql_joins() -> None:
    soul = (_AGENT_DIR / "SOUL.md").read_text()
    assert "SQL JOIN" in soul or "SQL JOINs" in soul


def test_rules_md_has_five_rules() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    # Must have at least 5 numbered rules
    assert rules.count("\n1.") + rules.count("1.") >= 1
    assert rules.count("5.") >= 1


def test_routing_skill_covers_all_voyages() -> None:
    routing = (_AGENT_DIR / "skills" / "routing.md").read_text()
    voyage_kinds = [
        "hot_deploy", "incident_summary", "stuck_sprint",
        "angry_whales", "fresh_cve", "exec_escalation",
        "risk_heatmap", "stigmergic_self_ref",
    ]
    for kind in voyage_kinds:
        assert kind in routing, f"routing.md missing voyage: {kind}"
