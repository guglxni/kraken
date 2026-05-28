"""Security regression tests for the hardening pass (OWASP audit follow-up).

Covers: voyage-name path traversal guard (F-10), fail-closed param typing
(F-1), API bearer-token auth (F-5), and webhook Content-Length limit (F-7).
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["KRAKEN_DEMO_MODE"] = "1"

from kraken import api as api_module  # noqa: E402
from kraken.voyages.compiler import VoyageCompileError, compile_voyage  # noqa: E402

# ── F-10: voyage-name path traversal ──────────────────────────────────────────

@pytest.mark.parametrize("bad_name", [
    "../../etc/passwd",
    "../secrets",
    "foo/bar",
    "UPPER",
    "with space",
    "x" * 100,
])
def test_compile_voyage_rejects_unsafe_names(bad_name: str) -> None:
    with pytest.raises(VoyageCompileError):
        compile_voyage(bad_name, {})


def test_compile_voyage_accepts_valid_slug() -> None:
    compiled = compile_voyage("exec_escalation", {})
    assert compiled.name == "exec_escalation"


# ── F-1: fail-closed param typing ─────────────────────────────────────────────

def test_unknown_param_type_is_rejected() -> None:
    from kraken.voyages.compiler import _coerce_param

    with pytest.raises(VoyageCompileError):
        _coerce_param("value", "mystery_type", "p", "v")


def test_string_param_quote_is_escaped() -> None:
    from kraken.voyages.compiler import _coerce_param

    out = _coerce_param("o'brien", "string", "p", "v")
    assert out == "o''brien"


def test_string_param_rejects_comment_injection() -> None:
    from kraken.voyages.compiler import _coerce_param

    with pytest.raises(VoyageCompileError):
        _coerce_param("1; DROP -- x", "string", "p", "v")


# ── F-5: API bearer-token auth ────────────────────────────────────────────────

@pytest.fixture
async def auth_client(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    # Enable the token guard for this test only.
    monkeypatch.setattr(api_module, "_API_TOKEN", "s3cr3t-token")
    transport = ASGITransport(app=api_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_protected_endpoint_requires_token(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/traces")
    assert resp.status_code == 401


async def test_protected_endpoint_rejects_wrong_token(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/traces", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 403


async def test_protected_endpoint_accepts_valid_token(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(
        "/api/traces", headers={"Authorization": "Bearer s3cr3t-token"}
    )
    assert resp.status_code == 200


async def test_health_is_open(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/health")
    assert resp.status_code == 200


# ── F-7: webhook Content-Length limit ─────────────────────────────────────────

async def test_webhook_rejects_oversized_content_length() -> None:
    from kraken.webhook_receiver import app as webhook_app

    transport = ASGITransport(app=webhook_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/webhook/github",
            content=b"{}",
            headers={"content-length": str(5 * 1024 * 1024)},
        )
    assert resp.status_code == 413
