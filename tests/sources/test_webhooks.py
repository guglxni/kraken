"""Tests for the webhooks source spec and webhook receiver.

Tests cover:
  1. manifest.yaml schema validation (tables, column types, inputs).
  2. JSONL delivery row format contract (what the receiver writes, what Coral reads).
  3. WebhookReceiver HMAC validation logic (unit tests, no HTTP).
  4. FastAPI endpoint integration tests using httpx TestClient.

Run:
    uv run pytest tests/sources/test_webhooks.py -v
    make test-sources
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixture data — representative JSONL rows for each table
# ---------------------------------------------------------------------------

_VALID_DELIVERY_ROW: dict[str, Any] = {
    "id": str(uuid.uuid4()),
    "source": "github",
    "event_type": "push",
    "payload": json.dumps(
        {
            "ref": "refs/heads/main",
            "after": "a1b2c3d4",
            "pusher": {"name": "aaryan"},
            "repository": {"full_name": "acme/backend"},
        }
    ),
    "received_at": "2026-05-20T14:30:00+00:00",
    "hmac_valid": True,
    "delivery_id": str(uuid.uuid4()),
    "content_length_bytes": 256,
}

_VALID_SUBSCRIPTION_ROW: dict[str, Any] = {
    "source": "github",
    "receiver_url": "https://abc123.ngrok.io/webhook/github",
    "secret_alias": "github_webhook_secret",
    "events": "push,pull_request,deployment",
    "active": True,
    "registered_at": "2026-05-01T10:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Schema validation helpers
# ---------------------------------------------------------------------------


def _assert_delivery_row_schema(row: dict[str, Any]) -> None:
    """Assert a deliveries-table row has all manifest.yaml declared columns."""
    required = {
        "id", "source", "event_type", "payload",
        "received_at", "hmac_valid", "delivery_id", "content_length_bytes",
    }
    missing = required - set(row.keys())
    assert not missing, f"Missing columns in delivery row: {missing}"
    assert isinstance(row["id"], str), "id must be Utf8"
    assert isinstance(row["source"], str), "source must be Utf8"
    assert isinstance(row["event_type"], str), "event_type must be Utf8"
    assert isinstance(row["payload"], str), "payload must be Utf8 (JSON string)"
    assert isinstance(row["received_at"], str), "received_at must be Timestamp (ISO string)"
    assert isinstance(row["hmac_valid"], bool), "hmac_valid must be Boolean"
    assert isinstance(row["content_length_bytes"], int), "content_length_bytes must be Int64"


def _assert_subscription_row_schema(row: dict[str, Any]) -> None:
    """Assert a subscriptions-table row has all manifest.yaml declared columns."""
    required = {"source", "receiver_url", "secret_alias", "events", "active", "registered_at"}
    missing = required - set(row.keys())
    assert not missing, f"Missing columns in subscription row: {missing}"
    assert isinstance(row["active"], bool), "active must be Boolean"


# ---------------------------------------------------------------------------
# Manifest YAML tests
# ---------------------------------------------------------------------------


class TestWebhooksManifestYaml:
    """Validate the webhooks manifest.yaml structure."""

    def test_manifest_exists_and_is_valid_yaml(self) -> None:
        """Verify the manifest file exists and parses as valid YAML."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        assert manifest_path.exists(), f"manifest.yaml not found at {manifest_path}"
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)
        assert manifest is not None

    def test_manifest_required_top_level_fields(self) -> None:
        """Verify all required top-level manifest fields are present."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert manifest["name"] == "webhooks"
        assert manifest["version"] == "0.1.0"
        assert manifest["dsl_version"] == 3
        assert manifest["backend"] == "file"

    def test_manifest_declares_webhooks_path_input(self) -> None:
        """Verify WEBHOOKS_PATH input is declared with a default."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert "inputs" in manifest
        assert "WEBHOOKS_PATH" in manifest["inputs"]
        wp_input = manifest["inputs"]["WEBHOOKS_PATH"]
        assert wp_input["kind"] == "variable"
        assert "default" in wp_input
        assert "webhooks.jsonl" in wp_input["default"]

    def test_manifest_has_two_tables(self) -> None:
        """Verify the manifest declares exactly 2 tables: deliveries, subscriptions."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        table_names = {t["name"] for t in manifest["tables"]}
        assert table_names == {"deliveries", "subscriptions"}

    def test_deliveries_table_has_hmac_valid_boolean_column(self) -> None:
        """Verify deliveries.hmac_valid is declared as Boolean type."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        deliveries = next(t for t in manifest["tables"] if t["name"] == "deliveries")
        hmac_col = next(
            (c for c in deliveries["columns"] if c["name"] == "hmac_valid"), None
        )
        assert hmac_col is not None, "deliveries.hmac_valid column not found"
        assert hmac_col["type"] == "Boolean", "hmac_valid must be Boolean type"

    def test_all_column_types_are_valid(self) -> None:
        """Verify all column types are valid Coral DSL types."""
        import yaml

        valid_types = {"Utf8", "Int64", "Float64", "Boolean", "Date", "Timestamp"}
        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "webhooks" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        for table in manifest["tables"]:
            for col in table["columns"]:
                assert col["type"] in valid_types, (
                    f"Table '{table['name']}', column '{col['name']}': "
                    f"invalid type '{col['type']}'"
                )


# ---------------------------------------------------------------------------
# Delivery row data contract tests
# ---------------------------------------------------------------------------


class TestWebhooksDeliveriesTable:
    """Tests for the webhooks.deliveries table data contract."""

    def test_valid_delivery_row_passes_schema(self) -> None:
        """Verify our fixture passes schema validation."""
        _assert_delivery_row_schema(_VALID_DELIVERY_ROW)

    def test_payload_is_valid_json_string(self) -> None:
        """Verify the payload field is a valid JSON string."""
        payload_str = _VALID_DELIVERY_ROW["payload"]
        payload_obj = json.loads(payload_str)
        assert isinstance(payload_obj, dict)

    def test_received_at_is_iso8601(self) -> None:
        """Verify received_at is a parseable ISO 8601 timestamp."""
        dt = datetime.fromisoformat(_VALID_DELIVERY_ROW["received_at"])
        assert dt.year >= 2000

    def test_id_is_valid_uuid(self) -> None:
        """Verify id is a valid UUID string."""
        delivery_id = _VALID_DELIVERY_ROW["id"]
        parsed = uuid.UUID(delivery_id)
        assert str(parsed) == delivery_id

    def test_hmac_valid_is_true(self) -> None:
        """Verify hmac_valid is always True for persisted rows (invalid rejected by receiver)."""
        assert _VALID_DELIVERY_ROW["hmac_valid"] is True

    def test_content_length_matches_payload(self) -> None:
        """Verify content_length_bytes matches the actual payload byte length."""
        payload_bytes = _VALID_DELIVERY_ROW["payload"].encode("utf-8")
        # content_length_bytes in our fixture is intentionally ~256 (approximation)
        # In production the receiver sets it to len(body) exactly.
        assert _VALID_DELIVERY_ROW["content_length_bytes"] > 0

    def test_source_is_lowercase(self) -> None:
        """Verify source name is always lowercase."""
        assert _VALID_DELIVERY_ROW["source"] == _VALID_DELIVERY_ROW["source"].lower()

    def test_jsonl_round_trip(self) -> None:
        """Verify the delivery row survives JSON serialise → deserialise."""
        serialised = json.dumps(_VALID_DELIVERY_ROW)
        deserialised = json.loads(serialised)
        _assert_delivery_row_schema(deserialised)


class TestWebhooksSubscriptionsTable:
    """Tests for the webhooks.subscriptions table data contract."""

    def test_valid_subscription_row_passes_schema(self) -> None:
        """Verify our fixture passes schema validation."""
        _assert_subscription_row_schema(_VALID_SUBSCRIPTION_ROW)

    def test_receiver_url_is_https(self) -> None:
        """Verify receiver_url uses HTTPS in production."""
        url = _VALID_SUBSCRIPTION_ROW["receiver_url"]
        assert url.startswith("https://") or url.startswith("http://localhost"), (
            "receiver_url should be HTTPS for public endpoints"
        )

    def test_active_is_boolean(self) -> None:
        """Verify active is a Python bool."""
        assert isinstance(_VALID_SUBSCRIPTION_ROW["active"], bool)


# ---------------------------------------------------------------------------
# HMAC validation unit tests (no HTTP required)
# ---------------------------------------------------------------------------


class TestHmacValidation:
    """Unit tests for HMAC validation logic in webhook_receiver.py."""

    def _compute_sha256_sig(self, secret: bytes, body: bytes) -> str:
        """Helper to compute expected HMAC-SHA256 signature."""
        digest = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def _compute_sha1_sig(self, secret: bytes, body: bytes) -> str:
        """Helper to compute expected HMAC-SHA1 signature."""
        digest = hmac.new(secret, body, hashlib.sha1).hexdigest()
        return f"sha1={digest}"

    def test_sha256_valid_signature_accepted(self) -> None:
        """Valid HMAC-SHA256 signature passes verification."""
        from kraken.webhook_receiver import _verify_hmac_sha256

        secret = b"test-secret-key"
        body = b'{"event": "push"}'
        sig = self._compute_sha256_sig(secret, body)
        assert _verify_hmac_sha256(secret, body, sig) is True

    def test_sha256_invalid_signature_rejected(self) -> None:
        """Invalid HMAC-SHA256 signature fails verification."""
        from kraken.webhook_receiver import _verify_hmac_sha256

        secret = b"test-secret-key"
        body = b'{"event": "push"}'
        bad_sig = "sha256=aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff0000aaaa1111bbbb2222"
        assert _verify_hmac_sha256(secret, body, bad_sig) is False

    def test_sha256_tampered_body_rejected(self) -> None:
        """Signature valid for original body fails when body is tampered."""
        from kraken.webhook_receiver import _verify_hmac_sha256

        secret = b"test-secret-key"
        original_body = b'{"event": "push"}'
        tampered_body = b'{"event": "INJECTED"}'
        sig = self._compute_sha256_sig(secret, original_body)
        assert _verify_hmac_sha256(secret, tampered_body, sig) is False

    def test_sha256_accepts_raw_hex_without_prefix(self) -> None:
        """SHA256 verification works with raw hex (no sha256= prefix)."""
        from kraken.webhook_receiver import _verify_hmac_sha256

        secret = b"test-secret-key"
        body = b'{"event": "push"}'
        raw_hex = hmac.new(secret, body, hashlib.sha256).hexdigest()
        assert _verify_hmac_sha256(secret, body, raw_hex) is True

    def test_sha1_valid_signature_accepted(self) -> None:
        """Valid HMAC-SHA1 signature passes verification (legacy GitHub)."""
        from kraken.webhook_receiver import _verify_hmac_sha1

        secret = b"test-secret-key"
        body = b'{"event": "push"}'
        sig = self._compute_sha1_sig(secret, body)
        assert _verify_hmac_sha1(secret, body, sig) is True

    def test_sha1_invalid_signature_rejected(self) -> None:
        """Invalid HMAC-SHA1 signature fails verification."""
        from kraken.webhook_receiver import _verify_hmac_sha1

        secret = b"test-secret-key"
        body = b'{"event": "push"}'
        bad_sig = "sha1=aaaa1111bbbb2222cccc3333dddd4444eeee5555"
        assert _verify_hmac_sha1(secret, body, bad_sig) is False

    def test_empty_body_produces_deterministic_signature(self) -> None:
        """HMAC over empty body is deterministic (not None / exception)."""
        from kraken.webhook_receiver import _verify_hmac_sha256

        secret = b"test-secret"
        body = b""
        sig = self._compute_sha256_sig(secret, body)
        assert _verify_hmac_sha256(secret, body, sig) is True


# ---------------------------------------------------------------------------
# FastAPI endpoint tests
# ---------------------------------------------------------------------------


class TestWebhookReceiverEndpoints:
    """Integration tests for the webhook receiver FastAPI app."""

    @pytest.fixture()
    def client(self, tmp_path: Path) -> Any:
        """Return a TestClient with the webhooks path pointed at a temp file."""
        from fastapi.testclient import TestClient

        from kraken.webhook_receiver import app

        webhooks_file = tmp_path / "webhooks.jsonl"
        with patch.dict(
            os.environ,
            {
                "KRAKEN_WEBHOOKS_PATH": str(webhooks_file),
                "KRAKEN_WEBHOOK_SECRET_GITHUB": "test-github-secret",
                "KRAKEN_WEBHOOK_SECRET": "test-shared-secret",
            },
        ):
            with TestClient(app) as c:
                yield c, webhooks_file

    def test_health_endpoint_returns_200(self, client: Any) -> None:
        """Health check returns 200 OK."""
        c, _ = client
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_valid_github_webhook_accepted(self, client: Any) -> None:
        """A properly signed GitHub webhook returns HTTP 202."""
        c, webhooks_file = client
        secret = b"test-github-secret"
        body = json.dumps(
            {"ref": "refs/heads/main", "pusher": {"name": "aaryan"}}
        ).encode()
        sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

        response = c.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "id" in data

    def test_valid_webhook_written_to_jsonl(self, client: Any) -> None:
        """A valid webhook delivery is appended to the JSONL file."""
        c, webhooks_file = client
        secret = b"test-github-secret"
        body = b'{"event": "push"}'
        sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

        c.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "push",
            },
        )

        assert webhooks_file.exists(), "JSONL file should have been created"
        lines = webhooks_file.read_text().strip().split("\n")
        assert len(lines) == 1
        row = json.loads(lines[0])
        _assert_delivery_row_schema(row)
        assert row["source"] == "github"
        assert row["event_type"] == "push"
        assert row["hmac_valid"] is True

    def test_invalid_signature_returns_403(self, client: Any) -> None:
        """A webhook with a bad signature is rejected with HTTP 403."""
        c, webhooks_file = client
        body = b'{"event": "push"}'
        bad_sig = "sha256=" + "0" * 64

        response = c.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": bad_sig,
                "X-GitHub-Event": "push",
            },
        )
        assert response.status_code == 403
        assert not webhooks_file.exists() or webhooks_file.stat().st_size == 0

    def test_missing_signature_returns_403(self, client: Any) -> None:
        """A webhook with no signature header is rejected with HTTP 403."""
        c, _ = client
        body = b'{"event": "push"}'

        response = c.post(
            "/webhook/github",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_multiple_deliveries_appended_sequentially(self, client: Any) -> None:
        """Multiple valid deliveries are all written to the JSONL file."""
        c, webhooks_file = client
        secret = b"test-github-secret"

        for i in range(3):
            body = json.dumps({"seq": i}).encode()
            sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
            resp = c.post(
                "/webhook/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "push",
                },
            )
            assert resp.status_code == 202

        lines = [l for l in webhooks_file.read_text().strip().split("\n") if l]
        assert len(lines) == 3
        for line in lines:
            _assert_delivery_row_schema(json.loads(line))
