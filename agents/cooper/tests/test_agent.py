"""Prompt tests for the Cooper agent."""

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
    assert spec["name"] == "cooper"
    assert spec["model"]["name"] == "claude-sonnet-4-6"
    assert spec["runtime"]["flow_role"] == "specialist"
    assert spec.get("isolation") == "worktree"


def test_coral_yaml_has_local_codebase() -> None:
    coral = yaml.safe_load((_AGENT_DIR / "tools" / "coral.yaml").read_text())
    sources = coral["tools"][0]["restrictions"]["allowed_sources"]
    assert "local_codebase" in sources


def test_hot_deploy_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "hot_deploy.md").exists()


def test_pr_drafting_skill_exists() -> None:
    assert (_AGENT_DIR / "skills" / "pr_drafting.md").exists()


def test_rules_mentions_no_merge() -> None:
    rules = (_AGENT_DIR / "RULES.md").read_text()
    assert "never" in rules.lower() and ("merge" in rules.lower() or "production" in rules.lower())
