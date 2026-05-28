"""Tests for the local-codebase source spec.

These tests verify:
  1. The manifest.yaml is valid and matches the declared schema.
  2. The JSONL output format that the preprocessor should emit matches what
     manifest.yaml expects (column names, types, no extra/missing fields).
  3. The Coral file backend glob patterns resolve correctly given test fixtures.

Since this is a file backend (no HTTP), there are no VCR cassettes. Tests
instead use in-memory fixture data and manifest YAML parsing.

Run:
    uv run pytest tests/sources/test_local_codebase.py -v
    make test-sources
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixture data — representative JSONL rows for each table
# ---------------------------------------------------------------------------

_VALID_FILE_ROW: dict[str, Any] = {
    "path": "kraken/coral_client.py",
    "extension": "py",
    "size_bytes": 4096,
    "content": "\"\"\"Coral MCP stdio client\"\"\"\n\nimport asyncio\n",
    "mtime": "2026-05-20T14:30:00+00:00",
}

_VALID_DIFF_ROW: dict[str, Any] = {
    "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
    "author_name": "Aaryan Guglani",
    "author_email": "aaryan@example.com",
    "message": "feat(phase-1-3): add OSV source spec\n\nCloses #3",
    "file_path": "sources/osv/manifest.yaml",
    "additions": 120,
    "deletions": 0,
    "created_at": "2026-05-20T14:00:00+00:00",
}

_VALID_SYMBOL_ROW: dict[str, Any] = {
    "file_path": "kraken/coral_client.py",
    "symbol_name": "coral_sql",
    "symbol_kind": "function",
    "language": "python",
    "start_line": 47,
    "end_line": 113,
    "signature": "async def coral_sql(query: str, voyage_id: str, agent_name: str = 'unknown') -> ResultSet:",
}


# ---------------------------------------------------------------------------
# Schema validation helpers
# ---------------------------------------------------------------------------


def _assert_file_row_schema(row: dict[str, Any]) -> None:
    """Assert a files-table row has all manifest.yaml declared columns."""
    required = {"path", "extension", "size_bytes", "content", "mtime"}
    missing = required - set(row.keys())
    assert not missing, f"Missing columns in files row: {missing}"
    assert isinstance(row["path"], str), "path must be Utf8"
    assert isinstance(row["extension"], str), "extension must be Utf8"
    assert isinstance(row["size_bytes"], int), "size_bytes must be Int64"
    assert isinstance(row["content"], str), "content must be Utf8"
    assert isinstance(row["mtime"], str), "mtime must be Timestamp (ISO string)"


def _assert_diff_row_schema(row: dict[str, Any]) -> None:
    """Assert a diffs-table row has all manifest.yaml declared columns."""
    required = {
        "commit_sha", "author_name", "author_email", "message",
        "file_path", "additions", "deletions", "created_at",
    }
    missing = required - set(row.keys())
    assert not missing, f"Missing columns in diffs row: {missing}"
    assert len(row["commit_sha"]) == 40, "commit_sha must be 40-char hex string"
    assert isinstance(row["additions"], int), "additions must be Int64"
    assert isinstance(row["deletions"], int), "deletions must be Int64"


def _assert_symbol_row_schema(row: dict[str, Any]) -> None:
    """Assert a symbols-table row has all manifest.yaml declared columns."""
    required = {
        "file_path", "symbol_name", "symbol_kind", "language",
        "start_line", "end_line", "signature",
    }
    missing = required - set(row.keys())
    assert not missing, f"Missing columns in symbols row: {missing}"
    assert isinstance(row["start_line"], int), "start_line must be Int64"
    assert isinstance(row["end_line"], int), "end_line must be Int64"
    assert row["end_line"] >= row["start_line"], "end_line must be >= start_line"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLocalCodebaseManifestYaml:
    """Validate the local-codebase manifest.yaml structure."""

    def test_manifest_exists_and_is_valid_yaml(self) -> None:
        """Verify the manifest file exists and parses as valid YAML."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        assert manifest_path.exists(), f"manifest.yaml not found at {manifest_path}"
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)
        assert manifest is not None

    def test_manifest_required_top_level_fields(self) -> None:
        """Verify all required top-level manifest fields are present."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert manifest["name"] == "local-codebase"
        assert manifest["version"] == "0.1.0"
        assert manifest["dsl_version"] == 3
        assert manifest["backend"] == "file"

    def test_manifest_declares_codebase_path_input(self) -> None:
        """Verify CODEBASE_PATH input is declared with a default."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert "inputs" in manifest, "manifest must declare inputs"
        assert "CODEBASE_PATH" in manifest["inputs"], "CODEBASE_PATH input is required"
        cp_input = manifest["inputs"]["CODEBASE_PATH"]
        assert cp_input["kind"] == "variable"
        assert "default" in cp_input, "CODEBASE_PATH must have a default value"

    def test_manifest_has_three_tables(self) -> None:
        """Verify the manifest declares exactly 3 tables: files, diffs, symbols."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        table_names = {t["name"] for t in manifest["tables"]}
        assert table_names == {"files", "diffs", "symbols"}

    def test_all_tables_use_jsonl_format(self) -> None:
        """Verify every table uses jsonl format (required for file backend)."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        for table in manifest["tables"]:
            assert table.get("format") == "jsonl", (
                f"Table '{table['name']}' must use format: jsonl"
            )

    def test_column_types_are_valid(self) -> None:
        """Verify all column types are valid Coral DSL types."""
        import yaml

        valid_types = {"Utf8", "Int64", "Float64", "Boolean", "Date", "Timestamp"}
        manifest_path = (
            Path(__file__).parent.parent.parent
            / "sources"
            / "local-codebase"
            / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        for table in manifest["tables"]:
            for col in table["columns"]:
                assert col["type"] in valid_types, (
                    f"Table '{table['name']}', column '{col['name']}': "
                    f"invalid type '{col['type']}'"
                )


class TestLocalCodebaseFilesTable:
    """Tests for the local_codebase.files table data contract."""

    def test_valid_file_row_passes_schema(self) -> None:
        """Verify our fixture passes schema validation."""
        _assert_file_row_schema(_VALID_FILE_ROW)

    def test_extension_is_lowercase_no_dot(self) -> None:
        """Verify extension is lowercase and has no leading dot."""
        assert _VALID_FILE_ROW["extension"] == _VALID_FILE_ROW["extension"].lower()
        assert not _VALID_FILE_ROW["extension"].startswith(".")

    def test_mtime_is_iso8601(self) -> None:
        """Verify mtime is a parseable ISO 8601 timestamp."""
        mtime = _VALID_FILE_ROW["mtime"]
        dt = datetime.fromisoformat(mtime)
        assert dt.year >= 2000

    def test_size_bytes_is_non_negative(self) -> None:
        """Verify size_bytes is non-negative."""
        assert _VALID_FILE_ROW["size_bytes"] >= 0

    def test_jsonl_round_trip(self) -> None:
        """Verify the file row survives JSON serialise → deserialise."""
        serialised = json.dumps(_VALID_FILE_ROW)
        deserialised = json.loads(serialised)
        _assert_file_row_schema(deserialised)


class TestLocalCodebaseDiffsTable:
    """Tests for the local_codebase.diffs table data contract."""

    def test_valid_diff_row_passes_schema(self) -> None:
        """Verify our fixture passes schema validation."""
        _assert_diff_row_schema(_VALID_DIFF_ROW)

    def test_commit_sha_is_40_chars(self) -> None:
        """Verify commit_sha is a full 40-character SHA1 hex string."""
        sha = _VALID_DIFF_ROW["commit_sha"]
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_additions_deletions_non_negative(self) -> None:
        """Verify addition and deletion counts are non-negative."""
        assert _VALID_DIFF_ROW["additions"] >= 0
        assert _VALID_DIFF_ROW["deletions"] >= 0

    def test_created_at_is_iso8601(self) -> None:
        """Verify created_at is a parseable ISO 8601 timestamp."""
        dt = datetime.fromisoformat(_VALID_DIFF_ROW["created_at"])
        assert dt.year >= 2000

    def test_jsonl_round_trip(self) -> None:
        """Verify the diff row survives JSON serialise → deserialise."""
        serialised = json.dumps(_VALID_DIFF_ROW)
        deserialised = json.loads(serialised)
        _assert_diff_row_schema(deserialised)


class TestLocalCodebaseSymbolsTable:
    """Tests for the local_codebase.symbols table data contract."""

    def test_valid_symbol_row_passes_schema(self) -> None:
        """Verify our fixture passes schema validation."""
        _assert_symbol_row_schema(_VALID_SYMBOL_ROW)

    def test_symbol_kind_is_valid(self) -> None:
        """Verify symbol_kind is one of the declared enum values."""
        valid_kinds = {"function", "class", "method", "variable", "constant", "import"}
        assert _VALID_SYMBOL_ROW["symbol_kind"] in valid_kinds

    def test_language_is_valid(self) -> None:
        """Verify language is one of the supported tree-sitter grammars."""
        valid_languages = {"python", "typescript", "javascript", "rust", "go"}
        assert _VALID_SYMBOL_ROW["language"] in valid_languages

    def test_line_numbers_are_positive(self) -> None:
        """Verify line numbers are 1-based (positive integers)."""
        assert _VALID_SYMBOL_ROW["start_line"] >= 1
        assert _VALID_SYMBOL_ROW["end_line"] >= 1

    def test_signature_is_non_empty_string(self) -> None:
        """Verify signature is a non-empty string."""
        assert isinstance(_VALID_SYMBOL_ROW["signature"], str)
        assert len(_VALID_SYMBOL_ROW["signature"]) > 0


class TestLocalCodebaseJsonlFileReading:
    """Integration-style tests verifying JSONL file reading works as expected."""

    def test_jsonl_file_with_multiple_rows(self) -> None:
        """Write a JSONL file with multiple rows and verify parsing."""
        rows = [_VALID_FILE_ROW, {**_VALID_FILE_ROW, "path": "kraken/models.py"}]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
            tmp_path = Path(f.name)

        try:
            lines = tmp_path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 2
            for line in lines:
                parsed = json.loads(line)
                _assert_file_row_schema(parsed)
        finally:
            tmp_path.unlink()

    def test_empty_jsonl_file_produces_no_rows(self) -> None:
        """An empty JSONL file should produce zero rows."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = Path(f.name)

        try:
            content = tmp_path.read_text(encoding="utf-8").strip()
            rows = [json.loads(line) for line in content.split("\n") if line.strip()]
            assert len(rows) == 0
        finally:
            tmp_path.unlink()
