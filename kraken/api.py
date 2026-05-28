"""KRAKEN FastAPI server — serves the Next.js frontend and SSE voyage streams.

Demo mode: set KRAKEN_DEMO_MODE=1 to serve fixture data from tests/fixtures/
without requiring a live Coral connection. Useful for demos and development.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from kraken.blackboard import get_blackboard
from kraken.voyages.compiler import (
    VoyageCompileError,
    compile_voyage,
    list_voyages,
)
from kraken.webhook_receiver import app as _webhook_app

logger = structlog.get_logger(__name__)

_DEMO_MODE = os.getenv("KRAKEN_DEMO_MODE", "0") == "1"
_FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
_API_TOKEN = os.getenv("KRAKEN_API_TOKEN", "")


def _require_auth(authorization: str | None = Header(default=None)) -> None:
    """Bearer token guard. No-op when KRAKEN_API_TOKEN is not set (dev/demo)."""
    if not _API_TOKEN:
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token> header")
    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token.encode(), _API_TOKEN.encode()):
        raise HTTPException(status_code=403, detail="Invalid API token")

# Allowlist of valid voyage names — prevents path traversal in fixture loading.
_VALID_VOYAGE_NAMES: frozenset[str] = frozenset({
    "hot_deploy",
    "incident_summary",
    "stuck_sprint",
    "angry_whales",
    "fresh_cve",
    "exec_escalation",
    "risk_heatmap",
    "stigmergic_self_ref",
})


def _load_fixture(voyage_name: str) -> dict[str, Any] | None:
    if voyage_name not in _VALID_VOYAGE_NAMES:
        return None
    path = _FIXTURES_DIR / f"{voyage_name}_result.json"
    if path.exists():
        return json.loads(path.read_text())  # type: ignore[return-value]
    return None


# Demo fixtures use human-readable voyage ids like "demo-v6-acme-001". Accept
# those in demo mode while still requiring a real UUID in production, so the
# IDOR protection on findings/reef-map holds for live deployments.
_DEMO_VOYAGE_ID_RE = re.compile(r"^demo-[a-z0-9-]{1,48}$")


def _validate_voyage_id(voyage_id: str) -> str:
    """Return a safe voyage_id or raise 422. UUID always; demo slugs in demo mode."""
    try:
        return str(uuid.UUID(voyage_id))
    except ValueError:
        if _DEMO_MODE and _DEMO_VOYAGE_ID_RE.match(voyage_id):
            return voyage_id
        raise HTTPException(
            status_code=422, detail="Invalid voyage_id — must be a UUID"
        ) from None


async def _record_demo_finding(voyage_name: str, fixture: dict[str, Any], params: dict[str, Any]) -> str:
    """Write a fixture-backed Finding to the blackboard so Reef Map + Spyglass
    populate in demo mode. Idempotent per voyage_id. Returns the voyage_id used."""
    demo_vid = str(fixture.get("voyage_id") or uuid.uuid4())
    bb = get_blackboard()
    if bb.read_findings(voyage_id=demo_vid):
        return demo_vid  # already seeded

    # Compile the voyage (pure Jinja2, no Coral needed) to attach real SQL +
    # sources for Spyglass provenance; fall back to fixture-declared values.
    sql = str(fixture.get("sql", ""))
    sources = fixture.get("sources_queried", [])
    try:
        compiled = compile_voyage(voyage_name, params)
        sql = compiled.sql
        sources = compiled.required_sources or sources
    except VoyageCompileError:
        pass

    from kraken.models import Finding

    rows = fixture.get("rows", [])
    finding = Finding(
        voyage_id=demo_vid,
        agent="quartermaster",
        kind=voyage_name,
        payload={
            "rows": rows,
            "row_count": fixture.get("row_count", len(rows)),
            "sources_queried": sources,
            "latency_ms": fixture.get("latency_ms", 500),
            "sql": sql,
            "params": params,
        },
    )
    await bb.awrite_finding(finding)
    logger.info("demo_finding_seeded", voyage=voyage_name, voyage_id=demo_vid)
    return demo_vid


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("kraken_api_startup", demo_mode=_DEMO_MODE, auth_enabled=bool(_API_TOKEN))
    # Fail closed: a non-demo deployment with no API token would expose every
    # data endpoint unauthenticated (F-5). Refuse to start in that case.
    if not _DEMO_MODE and not _API_TOKEN:
        raise RuntimeError(
            "KRAKEN_API_TOKEN is required when KRAKEN_DEMO_MODE != 1. "
            "Set a bearer token (openssl rand -hex 32) or run in demo mode."
        )
    get_blackboard()  # initialize parquet files
    try:
        from kraken.reef_memory import get_reef
        get_reef()
        logger.info("reef_memory_initialized")
    except Exception as exc:
        logger.warning("reef_memory_init_failed", error=str(exc))
    yield
    logger.info("kraken_api_shutdown")


app = FastAPI(
    title="KRAKEN API",
    description="Canonical developer surface for Coral — one SQL query, every system.",
    version="0.1.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "KRAKEN_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:8080",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    # Auth is a Bearer header, not cookies — credentials are unnecessary and
    # combining them with broad origins is a footgun (F-4).
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class VoyageRunRequest(BaseModel):
    voyage: str
    params: dict[str, Any] = {}
    voyage_id: str | None = None


class VoyageCompileRequest(BaseModel):
    voyage: str
    params: dict[str, Any] = {}


class QuestionRequest(BaseModel):
    question: str
    params: dict[str, Any] = {}
    voyage_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    params: dict[str, Any] = {}


# ── Voyage endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "kraken", "demo_mode": _DEMO_MODE}


@app.get("/api/voyages")
async def get_voyages() -> list[dict[str, Any]]:
    """List all registered voyages."""
    return list_voyages()


@app.post("/api/voyages/compile")
async def post_compile(req: VoyageCompileRequest, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Compile a voyage YAML to SQL without executing it."""
    try:
        compiled = compile_voyage(req.voyage, req.params)
        return {
            "name": compiled.name,
            "sql": compiled.sql,
            "required_sources": compiled.required_sources,
            "params": compiled.params,
            "output_schema": compiled.output_schema,
        }
    except VoyageCompileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/voyages/run")
async def post_run_voyage(req: VoyageRunRequest, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Run a voyage synchronously. For streaming, use /api/voyages/stream."""
    vid = req.voyage_id or str(uuid.uuid4())
    log = logger.bind(voyage=req.voyage, voyage_id=vid)
    log.info("api_voyage_run_start", demo_mode=_DEMO_MODE)

    if _DEMO_MODE:
        fixture = _load_fixture(req.voyage)
        if fixture:
            demo_vid = await _record_demo_finding(req.voyage, fixture, req.params)
            log.info("api_voyage_run_demo", voyage=req.voyage, voyage_id=demo_vid)
            return {"voyage_id": demo_vid, "status": "done", **fixture}
        raise HTTPException(status_code=404, detail=f"No fixture for voyage '{req.voyage}'")

    from kraken.crew import run

    try:
        result = await run(
            question=f"run voyage {req.voyage}",
            params=req.params,
            voyage_id=vid,
        )
        return {"voyage_id": vid, "status": "done", **result}
    except VoyageCompileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error("api_voyage_run_failed", error=str(exc), voyage_id=vid)
        raise HTTPException(
            status_code=500,
            detail={"message": "Voyage execution failed", "incident_id": vid},
        ) from exc


@app.post("/api/voyages/stream")
async def post_stream_voyage(req: VoyageRunRequest, request: Request, _: None = Depends(_require_auth)) -> EventSourceResponse:
    """Run a voyage with Server-Sent Events — streams progress events."""
    from kraken.voyages.compiler import compile_voyage

    if req.voyage not in _VALID_VOYAGE_NAMES:
        raise HTTPException(status_code=422, detail=f"Unknown voyage '{req.voyage}'")

    vid = req.voyage_id or str(uuid.uuid4())

    async def event_generator() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "start", "data": json.dumps({"voyage_id": vid, "voyage": req.voyage})}

        if _DEMO_MODE:
            fixture = _load_fixture(req.voyage)
            if not fixture:
                yield {"event": "error", "data": json.dumps({"error": f"No fixture for voyage '{req.voyage}'"})}
                return

            # Emit realistic SSE events from fixture data
            sources = fixture.get("sources_queried", [])
            sql_length = len(fixture.get("sql", "")) or 850
            yield {
                "event": "compiled",
                "data": json.dumps({"sources": sources, "sql_length": sql_length}),
            }
            yield {"event": "executing", "data": json.dumps({"target_agent": "quartermaster"})}
            rows = fixture.get("rows", [])
            yield {
                "event": "finding",
                "data": json.dumps({
                    "finding_id": f"demo-{vid[:8]}",
                    "row_count": fixture.get("row_count", len(rows)),
                    "rows": rows[:5],
                    "sources_queried": sources,
                    "latency_ms": fixture.get("latency_ms", 500),
                }),
            }
            yield {"event": "done", "data": json.dumps({"voyage_id": vid, "status": "done"})}
            return

        try:
            compiled = compile_voyage(req.voyage, req.params)
            yield {
                "event": "compiled",
                "data": json.dumps({
                    "sources": compiled.required_sources,
                    "sql_length": len(compiled.sql),
                }),
            }
        except VoyageCompileError as exc:
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}
            return

        try:
            from pathlib import Path

            import yaml

            from kraken.crew import run_voyage

            spec_path = Path(__file__).parent / "voyages" / f"{req.voyage}.yaml"
            spec = yaml.safe_load(spec_path.read_text()) if spec_path.exists() else {}
            target_agent = spec.get("target_agent", "quartermaster")

            yield {"event": "executing", "data": json.dumps({"target_agent": target_agent})}

            finding = await run_voyage(req.voyage, vid, target_agent, req.params)  # type: ignore[arg-type]

            yield {
                "event": "finding",
                "data": json.dumps({
                    "finding_id": finding.finding_id,
                    "row_count": finding.payload.get("row_count", 0),
                    "rows": finding.payload.get("rows", [])[:5],
                }),
            }
            yield {"event": "done", "data": json.dumps({"voyage_id": vid, "status": "done"})}

        except Exception as exc:
            logger.error("api_stream_failed", voyage=req.voyage, error=str(exc))
            yield {"event": "error", "data": json.dumps({"error": "Voyage execution failed"})}

    return EventSourceResponse(event_generator())


# ── Question endpoint (natural language → voyage) ─────────────────────────────

@app.post("/api/ask")
async def post_ask(req: QuestionRequest, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Natural-language question → voyage classification → results."""
    vid = req.voyage_id or str(uuid.uuid4())

    if _DEMO_MODE:
        # Classify question to a voyage by keyword matching
        q = req.question.lower()
        voyage_name = "exec_escalation"
        if "deploy" in q or "rollback" in q:
            voyage_name = "hot_deploy"
        elif "incident" in q or "error" in q or "spike" in q:
            voyage_name = "incident_summary"
        elif "sprint" in q or "ticket" in q or "stuck" in q:
            voyage_name = "stuck_sprint"
        elif "whale" in q or "churn" in q or "customer" in q:
            voyage_name = "angry_whales"
        elif "cve" in q or "vulnerability" in q or "security" in q:
            voyage_name = "fresh_cve"
        fixture = _load_fixture(voyage_name)
        if fixture:
            demo_vid = await _record_demo_finding(voyage_name, fixture, req.params)
            return {"voyage_id": demo_vid, "voyage": voyage_name, **fixture}
        raise HTTPException(status_code=404, detail=f"No fixture for voyage '{voyage_name}'")

    from kraken.crew import run

    try:
        result = await run(question=req.question, params=req.params, voyage_id=vid)
    except VoyageCompileError as exc:
        logger.warning("api_ask_compile_failed", error=str(exc), voyage_id=vid)
        raise HTTPException(
            status_code=422,
            detail={"message": "Could not build a voyage for that question", "incident_id": vid},
        ) from exc
    except Exception as exc:
        logger.error("api_ask_failed", error=str(exc), voyage_id=vid)
        raise HTTPException(
            status_code=500,
            detail={"message": "Question routing failed", "incident_id": vid},
        ) from exc
    return {"voyage_id": vid, **result}


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def post_chat(req: ChatRequest, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Natural-language message → voyage classification → plain reply string."""
    vid = str(uuid.uuid4())

    if _DEMO_MODE:
        q = req.message.lower()
        voyage_name = "exec_escalation"
        if "deploy" in q or "rollback" in q:
            voyage_name = "hot_deploy"
        elif "incident" in q or "error" in q or "spike" in q:
            voyage_name = "incident_summary"
        elif "sprint" in q or "ticket" in q or "stuck" in q:
            voyage_name = "stuck_sprint"
        elif "whale" in q or "churn" in q or "customer" in q:
            voyage_name = "angry_whales"
        elif "cve" in q or "vulnerability" in q or "security" in q:
            voyage_name = "fresh_cve"
        fixture = _load_fixture(voyage_name)
        rows = fixture.get("rows", []) if fixture else []
        reply = (
            f"Found {len(rows)} result(s) via voyage '{voyage_name}'."
            if rows
            else "No results for this query in demo mode."
        )
        return {"voyage_id": vid, "reply": reply}

    from kraken.crew import run

    try:
        result = await run(question=req.message, params=req.params, voyage_id=vid)
    except VoyageCompileError as exc:
        logger.warning("api_chat_compile_failed", error=str(exc), voyage_id=vid)
        raise HTTPException(
            status_code=422,
            detail={"message": "Could not build a voyage for that message", "incident_id": vid},
        ) from exc
    except Exception as exc:
        logger.error("api_chat_failed", error=str(exc), voyage_id=vid)
        raise HTTPException(
            status_code=500,
            detail={"message": "Chat query failed", "incident_id": vid},
        ) from exc

    findings = result.get("findings", [])
    reply = (
        f"Found {len(findings)} result(s)."
        if findings
        else result.get("answer", "Query complete — no results.")
    )
    return {"voyage_id": vid, "reply": reply}


# ── Blackboard endpoints ──────────────────────────────────────────────────────

@app.get("/api/findings")
async def get_findings(voyage_id: str | None = None, _: None = Depends(_require_auth)) -> list[dict[str, Any]]:
    """Read findings from the blackboard."""
    if voyage_id is not None:
        voyage_id = _validate_voyage_id(voyage_id)
    bb = get_blackboard()
    findings = bb.read_findings(voyage_id=voyage_id)
    return [
        {
            "finding_id": f.finding_id,
            "voyage_id": f.voyage_id,
            "agent": f.agent,
            "kind": f.kind,
            "payload": f.payload,
            "created_at": f.created_at.isoformat(),
        }
        for f in findings
    ]


@app.get("/api/reef-map/{voyage_id}")
async def get_reef_map(voyage_id: str, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Return Reef Map graph data for a completed voyage — nodes=sources, edges=JOINs."""
    safe_voyage_id = _validate_voyage_id(voyage_id)
    bb = get_blackboard()
    findings = bb.read_findings(voyage_id=safe_voyage_id)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_sources: set[str] = set()

    for finding in findings:  # type: ignore[assignment]
        sources = finding.payload.get("sources_queried", [])
        for src in sources:
            if src not in seen_sources:
                nodes.append({"id": src, "label": src, "type": _source_type(src)})
                seen_sources.add(src)

        for i, src_a in enumerate(sources):
            for src_b in sources[i + 1:]:
                edges.append({"source": src_a, "target": src_b, "voyage_id": voyage_id})

    return {"nodes": nodes, "edges": edges, "voyage_id": safe_voyage_id}


# ── Spyglass trace endpoints (findings + column lineage) ──────────────────────

def _finding_to_trace(finding: Any) -> dict[str, Any]:
    """Synthesise a Spyglass trace (with sqllineage column provenance) from a finding."""
    from kraken.lineage import extract_lineage

    payload = finding.payload
    sql = str(payload.get("sql", ""))
    return {
        "trace_id": finding.finding_id,
        "voyage_id": finding.voyage_id,
        "sql": sql,
        "plan": str(payload.get("plan", "")),
        "sources": payload.get("sources_queried", []),
        "duration_ms": payload.get("latency_ms", 0),
        "row_count": payload.get("row_count", 0),
        "created_at": finding.created_at.isoformat(),
        "lineage": extract_lineage(sql) if sql else {
            "tables": [], "columns": [], "nodes": [], "edges": [], "engine": "none",
        },
    }


@app.get("/api/traces")
async def get_traces(limit: int = 20, _: None = Depends(_require_auth)) -> list[dict[str, Any]]:
    """List recent voyage traces with SQL + column lineage for Spyglass."""
    bb = get_blackboard()
    findings = bb.read_findings()
    findings = sorted(findings, key=lambda f: f.created_at, reverse=True)[: max(1, min(limit, 100))]
    return [_finding_to_trace(f) for f in findings]


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str, _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Return a single trace by finding id, with column lineage."""
    bb = get_blackboard()
    for finding in bb.read_findings():
        if finding.finding_id == trace_id:
            return _finding_to_trace(finding)
    raise HTTPException(status_code=404, detail="Trace not found")


# ── Bench-O-Bot endpoint ──────────────────────────────────────────────────────

@app.get("/api/bench")
async def get_bench(voyage: str = "exec_escalation", _: None = Depends(_require_auth)) -> dict[str, Any]:
    """Run Bench-O-Bot for a voyage — KRAKEN vs direct-MCP comparison."""
    if voyage not in _VALID_VOYAGE_NAMES:
        raise HTTPException(status_code=422, detail=f"Unknown voyage '{voyage}'")
    from kraken.bench import bench_voyage

    result = await bench_voyage(voyage)
    return result.to_dict()


app.mount("/webhooks", _webhook_app)


def _source_type(source: str) -> str:
    if source in ("github",):
        return "vcs"
    if source in ("sentry", "datadog", "pagerduty"):
        return "observability"
    if source in ("stripe", "intercom"):
        return "crm"
    if source in ("linear", "jira"):
        return "pm"
    if source in ("osv",):
        return "security"
    if source in ("kraken_findings", "kraken_plans"):
        return "internal"
    return "other"
