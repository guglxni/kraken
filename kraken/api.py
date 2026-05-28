"""KRAKEN FastAPI server — serves the Next.js frontend and SSE voyage streams."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from kraken.blackboard import get_blackboard
from kraken.models import Finding, Plan, VoyageKind
from kraken.voyages.compiler import VoyageCompileError, compile_voyage, list_voyages, validate_voyage

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("kraken_api_startup")
    get_blackboard()  # initialize parquet files
    yield
    logger.info("kraken_api_shutdown")


app = FastAPI(
    title="KRAKEN API",
    description="Canonical developer surface for Coral — one SQL query, every system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# ── Voyage endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "kraken"}


@app.get("/api/voyages")
async def get_voyages() -> list[dict[str, Any]]:
    """List all registered voyages."""
    return list_voyages()


@app.post("/api/voyages/compile")
async def post_compile(req: VoyageCompileRequest) -> dict[str, Any]:
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
async def post_run_voyage(req: VoyageRunRequest) -> dict[str, Any]:
    """Run a voyage synchronously. For streaming, use /api/voyages/stream."""
    from kraken.crew import run

    vid = req.voyage_id or str(uuid.uuid4())
    log = logger.bind(voyage=req.voyage, voyage_id=vid)
    log.info("api_voyage_run_start")

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
        log.error("api_voyage_run_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Voyage failed: {exc}") from exc


@app.post("/api/voyages/stream")
async def post_stream_voyage(req: VoyageRunRequest, request: Request) -> EventSourceResponse:
    """Run a voyage with Server-Sent Events — streams progress events."""
    from kraken.crew import run_voyage
    from kraken.voyages.compiler import compile_voyage

    vid = req.voyage_id or str(uuid.uuid4())

    async def event_generator() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "start", "data": json.dumps({"voyage_id": vid, "voyage": req.voyage})}

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
            # Determine target agent from voyage YAML
            import yaml
            from pathlib import Path
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
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())


# ── Question endpoint (natural language → voyage) ─────────────────────────────

@app.post("/api/ask")
async def post_ask(req: QuestionRequest) -> dict[str, Any]:
    """Natural-language question → voyage classification → results."""
    from kraken.crew import run

    vid = req.voyage_id or str(uuid.uuid4())
    result = await run(question=req.question, params=req.params, voyage_id=vid)
    return {"voyage_id": vid, **result}


# ── Blackboard endpoints ──────────────────────────────────────────────────────

@app.get("/api/findings")
async def get_findings(voyage_id: str | None = None) -> list[dict[str, Any]]:
    """Read findings from the blackboard."""
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
async def get_reef_map(voyage_id: str) -> dict[str, Any]:
    """Return Reef Map graph data for a completed voyage — nodes=sources, edges=JOINs."""
    bb = get_blackboard()
    findings = bb.read_findings(voyage_id=voyage_id)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_sources: set[str] = set()

    for finding in findings:
        sources = finding.payload.get("sources_queried", [])
        for src in sources:
            if src not in seen_sources:
                nodes.append({"id": src, "label": src, "type": _source_type(src)})
                seen_sources.add(src)

        for i, src_a in enumerate(sources):
            for src_b in sources[i + 1:]:
                edges.append({"source": src_a, "target": src_b, "voyage_id": voyage_id})

    return {"nodes": nodes, "edges": edges, "voyage_id": voyage_id}


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
