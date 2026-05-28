"""Tests for KRAKEN API in KRAKEN_DEMO_MODE=1.

Verifies that all voyage endpoints serve fixture data without a live Coral
connection when the demo mode environment variable is set.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Patch env before importing the module so _DEMO_MODE is True at module load
os.environ["KRAKEN_DEMO_MODE"] = "1"

from kraken.api import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_reports_demo_mode(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["demo_mode"] is True
    assert body["status"] == "ok"


async def test_voyages_list(client: AsyncClient) -> None:
    resp = await client.get("/api/voyages")
    assert resp.status_code == 200
    voyages = resp.json()
    assert isinstance(voyages, list)
    names = [v["name"] for v in voyages]
    assert "exec_escalation" in names
    assert "hot_deploy" in names


@pytest.mark.parametrize("voyage_name", [
    "exec_escalation",
    "hot_deploy",
    "incident_summary",
    "angry_whales",
    "fresh_cve",
])
async def test_run_voyage_demo_serves_fixture(client: AsyncClient, voyage_name: str) -> None:
    resp = await client.post("/api/voyages/run", json={"voyage": voyage_name})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert "rows" in body
    assert "sources_queried" in body
    assert body["voyage"] == voyage_name


async def test_run_voyage_demo_unknown_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/api/voyages/run", json={"voyage": "nonexistent_voyage"})
    assert resp.status_code == 404


async def test_ask_demo_exec_escalation(client: AsyncClient) -> None:
    resp = await client.post("/api/ask", json={"question": "what is the executive escalation status?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "voyage_id" in body
    assert "rows" in body


async def test_ask_demo_routes_deploy_question(client: AsyncClient) -> None:
    resp = await client.post("/api/ask", json={"question": "should I rollback the latest deploy?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("voyage") == "hot_deploy"


async def test_ask_demo_routes_cve_question(client: AsyncClient) -> None:
    resp = await client.post("/api/ask", json={"question": "any new CVE vulnerabilities in our stack?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("voyage") == "fresh_cve"


async def test_ask_demo_routes_whale_question(client: AsyncClient) -> None:
    resp = await client.post("/api/ask", json={"question": "which customers are at churn risk?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("voyage") == "angry_whales"
