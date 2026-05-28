"""Tests for the new KRAKEN API surface in demo mode:
traces (with column lineage), Bench-O-Bot, and demo-mode blackboard seeding
that makes Reef Map + Spyglass populate.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["KRAKEN_DEMO_MODE"] = "1"

from kraken.api import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Demo-mode blackboard seeding (B1/B2) ──────────────────────────────────────

async def test_demo_run_seeds_blackboard_for_reef_map(client: AsyncClient) -> None:
    """Running a voyage in demo mode must populate Reef Map (was blank before)."""
    run = await client.post("/api/voyages/run", json={"voyage": "exec_escalation"})
    assert run.status_code == 200
    vid = run.json()["voyage_id"]

    reef = await client.get(f"/api/reef-map/{vid}")
    assert reef.status_code == 200
    body = reef.json()
    assert len(body["nodes"]) >= 3  # >=3 sources JOINed
    assert len(body["edges"]) >= 1


async def test_demo_run_populates_spyglass_traces(client: AsyncClient) -> None:
    await client.post("/api/voyages/run", json={"voyage": "exec_escalation"})
    traces = await client.get("/api/traces")
    assert traces.status_code == 200
    rows = traces.json()
    assert len(rows) >= 1
    t = rows[0]
    assert "trace_id" in t and "sql" in t and "lineage" in t
    assert t["lineage"]["engine"] in {"sqllineage", "sqlglot", "none"}


async def test_single_trace_lookup_and_404(client: AsyncClient) -> None:
    await client.post("/api/voyages/run", json={"voyage": "fresh_cve"})
    traces = (await client.get("/api/traces")).json()
    tid = traces[0]["trace_id"]
    one = await client.get(f"/api/traces/{tid}")
    assert one.status_code == 200
    assert one.json()["trace_id"] == tid

    missing = await client.get("/api/traces/does-not-exist")
    assert missing.status_code == 404


# ── Bench-O-Bot (B3) ──────────────────────────────────────────────────────────

async def test_bench_endpoint_returns_comparison(client: AsyncClient) -> None:
    resp = await client.get("/api/bench?voyage=exec_escalation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["voyage_name"] == "exec_escalation"
    assert "verdict" in body
    assert "latency_speedup" in body
    assert body["direct_mcp_simulated"] is True


async def test_bench_rejects_unknown_voyage(client: AsyncClient) -> None:
    resp = await client.get("/api/bench?voyage=nope")
    assert resp.status_code == 422


# ── voyage_id validation (IDOR guard, demo slug allowance) ────────────────────

async def test_reef_map_accepts_demo_slug_in_demo_mode(client: AsyncClient) -> None:
    resp = await client.get("/api/reef-map/demo-v6-acme-001")
    assert resp.status_code == 200  # demo slug allowed in demo mode


async def test_reef_map_rejects_garbage_voyage_id(client: AsyncClient) -> None:
    resp = await client.get("/api/reef-map/..%2f..%2fetc")
    assert resp.status_code in (404, 422)


async def test_findings_rejects_non_uuid_non_demo_slug(client: AsyncClient) -> None:
    resp = await client.get("/api/findings?voyage_id=' OR 1=1")
    assert resp.status_code == 422
