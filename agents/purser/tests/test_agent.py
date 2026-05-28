"""Prompt tests for the Purser agent (hero agent for exec_escalation)."""

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


def test_exec_escalation_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "exec_escalation.md").exists()


def test_angry_whales_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "angry_whales.md").exists()


def test_email_drafting_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "email_drafting.md").exists()


def test_mrr_weighting_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "mrr_weighting.md").exists()


def test_agent_yaml_schema() -> None:
    spec = yaml.safe_load((_AGENT_DIR / "agent.yaml").read_text())
    assert spec["name"] == "purser"
    assert spec["model"]["provider"] == "anthropic"
    assert spec["model"]["name"] == "claude-opus-4-6"
    assert spec["runtime"]["flow_role"] == "specialist"


def test_coral_yaml_has_composio_tools() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    tool_names = [t["name"] for t in coral["tools"]]
    assert "composio_draft_email" in tool_names, "Purser must have draft email tool"
    assert "coral_sql" in tool_names


def test_coral_yaml_draft_email_requires_anchor() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    draft_tool = next(t for t in coral["tools"] if t["name"] == "composio_draft_email")
    assert draft_tool.get("requires_anchor_approval") is True


def test_rules_md_mentions_anchor_approval() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    assert "Anchor" in rules or "anchor" in rules


def test_exec_escalation_skill_mentions_hero_demo() -> None:
    skill = (_AGENT_DIR / "skills" / "exec_escalation.md").read_text()
    assert "hero demo" in skill.lower() or "HERO" in skill


def test_soul_md_mentions_mrr() -> None:
    soul = (_AGENT_DIR / "SOUL.md").read_text()
    assert "MRR" in soul
