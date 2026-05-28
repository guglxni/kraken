"""CrewAI Flows orchestration — the KRAKEN agent runtime.

Flow: user question → Quartermaster classifies → writes Plan → specialist
agent executes voyage SQL via Coral → writes Findings → Quartermaster
synthesises → returns EscalationBrief / IncidentBrief / etc.

Agents NEVER call each other. All cross-agent state is the Parquet blackboard.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from crewai.flow.flow import Flow, listen, start

from kraken.blackboard import get_blackboard
from kraken.coral_client import coral_sql
from kraken.models import (
    AgentName,
    Finding,
    Plan,
    VoyageKind,
)
from kraken.reef_memory import get_reef
from kraken.voyages.compiler import VoyageCompileError, compile_voyage

logger = structlog.get_logger(__name__)

# ── Agent identity loaders ────────────────────────────────────────────────────

def _load_agent_spec(name: str) -> dict[str, Any]:
    """Load agent YAML spec from agents/{name}/agent.yaml."""
    from pathlib import Path

    import yaml

    path = Path(__file__).parent.parent / "agents" / name / "agent.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Agent spec not found: {path}")
    return yaml.safe_load(path.read_text())  # type: ignore[no-any-return]


def _load_soul(name: str) -> str:
    from pathlib import Path
    path = Path(__file__).parent.parent / "agents" / name / "SOUL.md"
    return path.read_text() if path.exists() else ""


def _load_rules(name: str) -> str:
    from pathlib import Path
    path = Path(__file__).parent.parent / "agents" / name / "RULES.md"
    return path.read_text() if path.exists() else ""


# ── Voyage runner ─────────────────────────────────────────────────────────────

async def run_voyage(
    voyage_name: str,
    voyage_id: str,
    agent_name: AgentName,
    params: dict[str, Any],
) -> Finding:
    """Compile and execute a voyage, returning a Finding for the blackboard."""
    log = logger.bind(voyage=voyage_name, voyage_id=voyage_id, agent=agent_name)

    try:
        compiled = compile_voyage(voyage_name, params)
    except VoyageCompileError as exc:
        log.error("voyage_compile_failed", error=str(exc))
        bb = get_blackboard()
        finding = Finding(
            voyage_id=voyage_id,
            agent=agent_name,
            kind="error",
            payload={"error": str(exc), "voyage": voyage_name},
        )
        await bb.awrite_finding(finding)
        return finding

    log.info("voyage_compiled", sources=compiled.required_sources)

    result = await coral_sql(compiled.sql, voyage_id=voyage_id, agent_name=agent_name)

    finding = Finding(
        voyage_id=voyage_id,
        agent=agent_name,
        kind=voyage_name,
        payload={
            "rows": result.rows,
            "row_count": result.row_count,
            "cache_hit": result.cache_hit,
            "latency_ms": result.latency_ms,
            "sources_queried": result.sources_queried,
            "params": params,
            "sql": compiled.sql,
        },
    )

    bb = get_blackboard()
    await bb.awrite_finding(finding)
    log.info("voyage_finding_written", row_count=result.row_count, finding_id=finding.finding_id)
    return finding


# ── Quartermaster synthesis ───────────────────────────────────────────────────

async def synthesise_findings(voyage_id: str) -> dict[str, Any]:
    """Read all findings for a voyage and synthesise into a final answer."""
    # Validate voyage_id is a UUID before embedding in SQL (C-1 SQL injection prevention)
    try:
        safe_voyage_id = str(uuid.UUID(voyage_id))
    except ValueError:
        logger.warning("synthesise_invalid_voyage_id", voyage_id=voyage_id[:64])
        return {"voyage_id": voyage_id, "findings": []}

    bb = get_blackboard()
    findings = bb.read_findings(voyage_id=safe_voyage_id)

    if not findings:
        return {"answer": "No findings produced. Check Coral source connectivity.", "findings": []}

    # Query findings table via Coral for structured synthesis — voyage_id is UUID-validated
    synthesis_sql = f"""
    SELECT
      f.agent,
      f.kind,
      f.payload,
      f.created_at
    FROM kraken_findings.findings f
    WHERE f.voyage_id = '{safe_voyage_id}'
    ORDER BY f.created_at ASC
    """
    try:
        result = await coral_sql(synthesis_sql, voyage_id=safe_voyage_id, agent_name="quartermaster")
        return {
            "voyage_id": safe_voyage_id,
            "findings": [f.payload for f in findings],
            "rows": result.rows,
        }
    except Exception:
        # Fallback: return raw findings without Coral synthesis
        return {
            "voyage_id": safe_voyage_id,
            "findings": [f.payload for f in findings],
        }


# ── Flow definition ───────────────────────────────────────────────────────────

class KrakenFlow(Flow):  # type: ignore[misc]
    """
    Main KRAKEN orchestration flow.

    State dict keys:
      question: str
      voyage_id: str
      voyage_kind: VoyageKind
      params: dict
      plan: Plan | None
      result: dict | None
    """

    @start()
    async def classify(self) -> dict[str, Any]:
        question: str = self.state.get("question", "")
        voyage_id: str = self.state.get("voyage_id", str(uuid.uuid4()))
        self.state["voyage_id"] = voyage_id

        log = logger.bind(voyage_id=voyage_id, question=question[:80])
        log.info("kraken_flow_start")

        # Quartermaster classifies question into voyage kind via Coral schema discovery
        classify_sql = """
        SELECT
          t.table_name                                AS source_table,
          t.description
        FROM coral.tables t
        ORDER BY t.table_name
        LIMIT 50
        """
        try:
            await coral_sql(classify_sql, voyage_id=voyage_id, agent_name="quartermaster")
        except Exception as exc:
            log.warning("coral_schema_discovery_failed", error=str(exc))

        # Determine voyage kind from question keywords (heuristic; LLM routing in full impl)
        kind = _classify_question(question)
        self.state["voyage_kind"] = kind
        log.info("voyage_classified", kind=kind)

        # Inject Reef exemplars as few-shot context for the Quartermaster
        exemplars = get_reef().recall(question, top_k=3)
        if exemplars:
            log.info("reef_exemplars_injected", count=len(exemplars))
        self.state["exemplars"] = exemplars

        return self.state

    @listen(classify)
    async def dispatch(self, state: dict[str, Any]) -> dict[str, Any]:
        voyage_id = state["voyage_id"]
        kind = state["voyage_kind"]
        params = state.get("params", {})

        agent_map: dict[str, AgentName] = {
            "hot_deploy": "cooper",       # V1: Cooper is the Coding Debugger
            "incident_summary": "helm",   # V2: Helm is the SRE Investigator
            "stuck_sprint": "bosun",      # V3: Bosun is Sprint Health
            "angry_whales": "purser",     # V4: Purser is Customer Escalation
            "fresh_cve": "lookout",       # V5: Lookout is Security & Compliance
            "exec_escalation": "purser",  # V6: Purser (HERO voyage)
            "risk_heatmap": "helm",       # V7: Helm (morning briefing)
            "stigmergic_self_ref": "lookout",  # V8: Lookout (self-reference)
        }
        target: AgentName = agent_map.get(kind, "quartermaster")

        bb = get_blackboard()
        plan = Plan(
            voyage_id=voyage_id,
            kind=kind,
            target_agent=target,
            params=params,
            priority=state.get("priority", "medium"),
        )
        await bb.awrite_plan(plan)
        self.state["plan"] = plan.model_dump()

        logger.bind(voyage_id=voyage_id).info(
            "plan_dispatched", kind=kind, target=target, plan_id=plan.plan_id
        )
        return self.state

    @listen(dispatch)
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        voyage_id = state["voyage_id"]
        kind = state["voyage_kind"]
        plan_data = state.get("plan", {})
        params = plan_data.get("params", state.get("params", {}))
        target: AgentName = plan_data.get("target_agent", "quartermaster")

        bb = get_blackboard()
        plan_id = plan_data.get("plan_id", "")
        if plan_id:
            await bb.aupdate_plan_status(plan_id, "running")

        finding = await run_voyage(kind, voyage_id, target, params)

        if plan_id:
            status = "done" if finding.kind != "error" else "failed"
            await bb.aupdate_plan_status(plan_id, status)

        # Persist finding in Reef Memory for future exemplar recall
        if finding.kind != "error":
            get_reef().store(
                voyage_id=voyage_id,
                question=state.get("question", kind),
                kind=kind,
                payload=finding.payload,
            )

        self.state["finding"] = finding.model_dump()
        return self.state

    @listen(execute)
    async def synthesise(self, state: dict[str, Any]) -> dict[str, Any]:
        voyage_id = state["voyage_id"]
        result = await synthesise_findings(voyage_id)
        self.state["result"] = result
        logger.bind(voyage_id=voyage_id).info("voyage_complete", rows=result.get("row_count", 0))
        return self.state


def _classify_question(question: str) -> VoyageKind:
    """Keyword heuristic for voyage classification.

    The full implementation uses an LLM call via PydanticAI with the routing.md skill
    as a few-shot prompt. This heuristic is the fallback used in tests and the CLI
    when no LLM is available.
    """
    q = question.lower()
    # V6 exec_escalation — check first (highest-value, most specific trigger)
    if any(w in q for w in ["escalation", "exec", "executive", "c-suite", "churning",
                             "urgent", "gmail", "email from"]):
        return "exec_escalation"
    # V1 hot_deploy
    if any(w in q for w in ["deploy", "rollback", "release", "push", "shipping", "on fire",
                             "regression", "who broke"]):
        return "hot_deploy"
    # V2 incident_summary
    if any(w in q for w in ["incident", "outage", "down", "degraded", "pagerduty", "paged",
                             "sla breach", "auto-summarize"]):
        return "incident_summary"
    # V3 stuck_sprint
    if any(w in q for w in ["sprint", "blocked", "stuck", "jira", "linear", "velocity",
                             "slipping", "delivery risk"]):
        return "stuck_sprint"
    # V4 angry_whales
    if any(w in q for w in ["churn", "whale", "cancel", "angry", "customer", "billing",
                             "open tickets", "enterprise"]):
        return "angry_whales"
    # V5 fresh_cve
    if any(w in q for w in ["cve", "vulnerability", "security", "ghsa", "exploit",
                             "cvss", "patch", "sbom"]):
        return "fresh_cve"
    # V7 risk_heatmap
    if any(w in q for w in ["risk", "heatmap", "briefing", "morning", "overview", "what's on fire",
                             "daily", "standup"]):
        return "risk_heatmap"
    # V8 stigmergic_self_ref
    if any(w in q for w in ["kraken", "self", "voyage history", "metrics", "performance",
                             "prior findings", "already flagged"]):
        return "stigmergic_self_ref"
    return "exec_escalation"  # default to hero voyage


# ── Public API ────────────────────────────────────────────────────────────────

async def run(
    question: str,
    params: dict[str, Any] | None = None,
    voyage_id: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """Entry point: run a KRAKEN voyage from a natural-language question."""
    flow = KrakenFlow()
    flow.state.update({
        "question": question,
        "voyage_id": voyage_id or str(uuid.uuid4()),
        "params": params or {},
        "priority": priority,
    })
    await flow.kickoff_async()
    return flow.state.get("result", {})


def run_sync(
    question: str,
    params: dict[str, Any] | None = None,
    voyage_id: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for CLI / testing use."""
    return asyncio.run(run(question, params=params, voyage_id=voyage_id))
