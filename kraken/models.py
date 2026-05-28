"""Pydantic models for all agent handoffs and findings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

VoyageKind = Literal[
    "hot_deploy",
    "incident_summary",
    "stuck_sprint",
    "angry_whales",
    "fresh_cve",
    "exec_escalation",
    "risk_heatmap",
    "stigmergic_self_ref",
]

AgentName = Literal["quartermaster", "helm", "cooper", "bosun", "purser", "lookout"]
Priority = Literal["low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]
SuggestedAction = Literal["draft_reply", "page_oncall", "rollback", "create_ticket"]


class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    voyage_id: str
    kind: VoyageKind
    target_agent: Literal["helm", "cooper", "bosun", "purser", "lookout"]
    priority: Priority = "medium"
    params: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "running", "done", "failed"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    voyage_id: str
    agent: AgentName
    kind: str
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EscalationBrief(BaseModel):
    customer: str
    mrr: float
    root_cause: str
    blast_radius: str
    suggested_actions: list[SuggestedAction]
    confidence: Confidence
    evidence: list[str]  # SQL snippets supporting the claim


class IncidentBrief(BaseModel):
    incident_id: str
    title: str
    suspect_deploy: str | None
    suspect_pr: str | None
    author: str | None
    third_party_outage: str | None
    confidence: Confidence
    evidence: list[str]


class SprintBrief(BaseModel):
    stuck_issues: list[dict[str, Any]]
    blockers: list[str]
    suggested_actions: list[str]


class CVEBrief(BaseModel):
    cve_id: str
    summary: str
    severity_score: float
    deploy_id: str | None
    author: str | None
    policy_doc: str | None
    confidence: Confidence


class CompiledVoyage(BaseModel):
    name: str
    sql: str
    required_sources: list[str]
    params: dict[str, Any]
    output_schema: list[dict[str, str]]


class ResultSet(BaseModel):
    rows: list[dict[str, Any]]
    row_count: int
    cache_hit: bool = False
    latency_ms: float = 0.0
    sources_queried: list[str] = Field(default_factory=list)
