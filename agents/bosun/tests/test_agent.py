"""Prompt tests for the Bosun agent."""

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
    assert spec["name"] == "bosun"
    assert spec["model"]["name"] == "claude-haiku-4-5"
    assert spec["max_turns"] == 5
    assert spec["runtime"]["flow_role"] == "specialist"


def test_coral_yaml_has_linear() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    sources = coral["tools"][0]["restrictions"]["allowed_sources"]
    assert "linear" in sources
    assert "jira" in sources


def test_stuck_sprint_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "stuck_sprint.md").exists()


def test_rules_no_scheduling_decisions() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    assert "scheduling" in rules.lower()
