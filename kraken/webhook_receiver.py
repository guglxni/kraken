"""KRAKEN Webhook Receiver — FastAPI HMAC-validated webhook ingestion server.

Listens on port 9000. For each inbound POST /webhook/<source> request:
  1. Reads the raw body and the provider-specific signature header.
  2. Validates the HMAC-SHA256 (or SHA1 for legacy GitHub) signature against
     the per-source secret stored in the Supabase credential store.
  3. Rejects invalid signatures with HTTP 403.
  4. Appends the validated delivery as a JSONL row to ~/.kraken/webhooks.jsonl
     so that the Coral webhooks source can query it immediately.

Run via:
    kraken webhook:serve           (via kraken CLI)
    uvicorn kraken.webhook_receiver:app --port 9000

Architecture note (CLAUDE.md Rule 2):
  This receiver is write-side infrastructure. It captures incoming events and
  stores them locally. Agents read deliveries via Coral SQL (webhooks.deliveries)
  — they never import this module or call it directly.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

_DEFAULT_WEBHOOKS_PATH = Path("~/.kraken/webhooks.jsonl").expanduser()
_DEFAULT_PORT = 9000

# Per-source signature header names and HMAC algorithms.
# Provider-specific: extend this dict when adding new sources.
_SOURCE_SIG_HEADERS: dict[str, tuple[str, str]] = {
    "github": ("x-hub-signature-256", "sha256"),
    "sentry": ("sentry-hook-signature", "sha256"),
    "stripe": ("stripe-signature", "sha256"),
    "pagerduty": ("x-webhook-signature", "sha256"),
    "linear": ("linear-signature", "sha256"),
    # Legacy GitHub SHA1 — prefer sha256 but keep for compatibility
    "github-legacy": ("x-hub-signature", "sha1"),
}

# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="KRAKEN Webhook Receiver",
    description="HMAC-validated webhook ingestion for Coral webhooks source",
    version="0.1.0",
    docs_url="/debug/docs",
    redoc_url=None,
)


def _get_webhooks_path() -> Path:
    """Resolve the JSONL output path from env or default."""
    raw = os.environ.get("KRAKEN_WEBHOOKS_PATH", str(_DEFAULT_WEBHOOKS_PATH))
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_secret(source: str) -> bytes:
    """Load the HMAC secret for a given source.

    Precedence:
    1. KRAKEN_WEBHOOK_SECRET_<SOURCE_UPPER> env var (for local dev)
    2. KRAKEN_WEBHOOK_SECRET env var (single shared secret for testing)

    In production, secrets are stored in the Supabase credential store and
    injected into the environment by the KRAKEN launcher before this process
    starts.

    Raises:
        HTTPException 500 if no secret is configured for the source.
    """
    env_key = f"KRAKEN_WEBHOOK_SECRET_{source.upper().replace('-', '_')}"
    secret_str = os.environ.get(env_key) or os.environ.get("KRAKEN_WEBHOOK_SECRET")
    if not secret_str:
        logger.error("webhook_secret_missing", source=source)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No HMAC secret configured for source '{source}'. "
            f"Set {env_key} or KRAKEN_WEBHOOK_SECRET.",
        )
    return secret_str.encode()


def _verify_hmac_sha256(secret: bytes, body: bytes, signature_header: str) -> bool:
    """Verify a HMAC-SHA256 signature.

    Accepts both 'sha256=<hex>' format (GitHub style) and raw hex.
    Returns True if the signature matches, False otherwise.
    Comparison is always constant-time to prevent timing attacks.
    """
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    # Strip the 'sha256=' prefix if present
    provided = signature_header.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, provided)


def _verify_hmac_sha1(secret: bytes, body: bytes, signature_header: str) -> bool:
    """Verify a legacy HMAC-SHA1 signature (GitHub v1 format)."""
    expected = hmac.new(secret, body, hashlib.sha1).hexdigest()
    provided = signature_header.removeprefix("sha1=").strip()
    return hmac.compare_digest(expected, provided)


def _append_delivery(delivery: dict[str, object]) -> None:
    """Atomically append a delivery JSON line to the JSONL file."""
    path = _get_webhooks_path()
    line = json.dumps(delivery, ensure_ascii=False, default=str) + "\n"
    # 'a' mode is append; on most POSIX systems a single write() is atomic
    # for lines under the pipe buffer limit (~4 KB). For larger payloads,
    # a file lock would be needed — acceptable for hackathon scope.
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


# ── Routes ─────────────────────────────────────────────────────────────────────


@app.post(
    "/webhook/{source}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive and validate a webhook delivery",
)
async def receive_webhook(
    source: str,
    request: Request,
    x_delivery_id: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """Accept a webhook delivery, validate its HMAC signature, and persist it.

    Path parameters:
        source: Originating service name (github, sentry, stripe, pagerduty,
                linear). Must match a configured secret.

    Returns HTTP 202 on success, HTTP 403 on signature failure.
    """
    # Read raw body first — must happen before any other body parsing
    body = await request.body()

    # Determine which signature header and algorithm to use for this source
    source_lower = source.lower()
    sig_config = _SOURCE_SIG_HEADERS.get(source_lower)
    if sig_config is None:
        # Unknown source — still persist but mark as unverified
        logger.warning("webhook_unknown_source", source=source)
        sig_header_name, algorithm = "x-webhook-signature", "sha256"
    else:
        sig_header_name, algorithm = sig_config

    # Extract the signature header value
    signature_value = request.headers.get(sig_header_name, "")
    if not signature_value:
        logger.warning(
            "webhook_missing_signature",
            source=source,
            expected_header=sig_header_name,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing signature header '{sig_header_name}'",
        )

    # Load and verify
    secret = _load_secret(source_lower)
    if algorithm == "sha256":
        valid = _verify_hmac_sha256(secret, body, signature_value)
    else:
        valid = _verify_hmac_sha1(secret, body, signature_value)

    if not valid:
        logger.warning("webhook_invalid_signature", source=source)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HMAC signature verification failed",
        )

    # Determine event type from provider-specific header
    event_type = (
        request.headers.get("x-github-event")
        or request.headers.get("sentry-hook-resource")
        or request.headers.get("stripe-event-type")
        or request.headers.get("x-pagerduty-signature", "").split("=")[0]
        or request.headers.get("linear-event", "unknown")
    )

    delivery_id = x_github_delivery or x_delivery_id or str(uuid.uuid4())
    received_at = datetime.now(UTC).isoformat()

    delivery: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "source": source_lower,
        "event_type": event_type,
        "payload": body.decode("utf-8", errors="replace"),
        "received_at": received_at,
        "hmac_valid": True,
        "delivery_id": delivery_id,
        "content_length_bytes": len(body),
    }

    _append_delivery(delivery)

    logger.info(
        "webhook_accepted",
        source=source_lower,
        event_type=event_type,
        delivery_id=delivery_id,
        bytes=len(body),
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "accepted", "id": delivery["id"]},
    )


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Return 200 OK when the receiver is running."""
    path = _get_webhooks_path()
    return {
        "status": "ok",
        "webhooks_path": str(path),
    }


# ── Entrypoint ─────────────────────────────────────────────────────────────────


def serve(port: int = _DEFAULT_PORT, host: str = "0.0.0.0") -> None:  # noqa: S104
    """Start the webhook receiver. Called by kraken CLI webhook:serve command."""
    import uvicorn  # imported here so the module can be imported without uvicorn

    logger.info("webhook_receiver_starting", host=host, port=port)
    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    serve()
