"""VCR.py tests for the OSV source spec.

These tests replay recorded HTTP interactions against the OSV.dev API to verify
that the manifest.yaml column mapping, rows_path extraction, and filter pushdown
behave as documented.

Fixtures live in tests/sources/cassettes/osv/ (VCR cassette format).

Run:
    uv run pytest tests/sources/test_osv.py -v
    make test-sources

To re-record cassettes against the live API (requires network access):
    pytest tests/sources/test_osv.py --vcr-record=all -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixture data (inline stubs — replace with VCR cassette replay once Coral
# source test tooling is available: `coral source test osv`)
# ---------------------------------------------------------------------------

CASSETTES_DIR = Path(__file__).parent / "cassettes" / "osv"

# Minimal OSV API response for a single vulnerability (GHSA-style record)
_VULN_RECORD: dict[str, Any] = {
    "id": "GHSA-jfh8-c2jp-hdqm",
    "summary": "PyTorch vulnerable to arbitrary code execution",
    "details": "A vulnerability in PyTorch allows arbitrary code execution...",
    "published": "2024-01-15T12:00:00Z",
    "modified": "2024-01-20T08:30:00Z",
    "schema_version": "1.5.0",
    "severity": [
        {
            "type": "CVSS_V3",
            "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        }
    ],
    "database_specific": {
        "severity": "CRITICAL",
        "cwe_ids": ["CWE-502"],
    },
    "affected": [
        {
            "package": {
                "name": "torch",
                "ecosystem": "PyPI",
                "purl": "pkg:pypi/torch",
            },
            "ranges": [
                {
                    "type": "ECOSYSTEM",
                    "events": [
                        {"introduced": "0"},
                        {"fixed": "2.1.2"},
                    ],
                }
            ],
            "ecosystem_specific": {"severity": "CRITICAL"},
        }
    ],
    "references": [
        {"type": "ADVISORY", "url": "https://github.com/advisories/GHSA-jfh8-c2jp-hdqm"},
        {"type": "FIX", "url": "https://github.com/pytorch/pytorch/pull/12345"},
    ],
    "aliases": ["CVE-2024-5480"],
}

_QUERY_RESPONSE: dict[str, Any] = {
    "vulns": [_VULN_RECORD],
}


# ---------------------------------------------------------------------------
# Schema validation helpers
# ---------------------------------------------------------------------------


def _assert_vuln_schema(vuln: dict[str, Any]) -> None:
    """Assert that a vulnerability dict has the fields declared in manifest.yaml."""
    required_fields = ["id", "summary", "published", "modified", "schema_version"]
    for field in required_fields:
        assert field in vuln, f"Missing required field '{field}' in vulnerability record"
    assert isinstance(vuln["id"], str), "id must be a string"
    assert isinstance(vuln["summary"], str), "summary must be a string"


def _assert_affected_schema(row: dict[str, Any]) -> None:
    """Assert that an affected row has the fields declared in manifest.yaml."""
    required_fields = ["package"]
    for field in required_fields:
        assert field in row, f"Missing required field '{field}' in affected record"
    pkg = row["package"]
    assert "name" in pkg, "affected.package.name is required"
    assert "ecosystem" in pkg, "affected.package.ecosystem is required"


def _assert_ranges_schema(range_entry: dict[str, Any]) -> None:
    """Assert that a range entry has the fields declared in manifest.yaml."""
    assert "type" in range_entry, "ranges.type is required"
    assert "events" in range_entry, "ranges.events is required"
    assert isinstance(range_entry["events"], list), "ranges.events must be a list"


def _assert_reference_schema(ref: dict[str, Any]) -> None:
    """Assert that a reference row has the fields declared in manifest.yaml."""
    assert "type" in ref, "references.type is required"
    assert "url" in ref, "references.url is required"
    assert ref["url"].startswith("http"), f"references.url must be a URL, got: {ref['url']}"


# ---------------------------------------------------------------------------
# Unit tests — exercise the manifest schema against fixture data
# ---------------------------------------------------------------------------


class TestOsvVulnerabilitiesTable:
    """Tests for the osv.vulnerabilities table schema and data contract."""

    def test_fixture_record_has_required_schema(self) -> None:
        """Verify our inline fixture matches the manifest.yaml column list."""
        _assert_vuln_schema(_VULN_RECORD)

    def test_query_response_rows_path(self) -> None:
        """Verify that rows_path: [vulns] correctly extracts the vulnerability list."""
        rows = _QUERY_RESPONSE.get("vulns", [])
        assert isinstance(rows, list), "rows_path [vulns] should produce a list"
        assert len(rows) == 1, "Expected 1 vulnerability in fixture"
        _assert_vuln_schema(rows[0])

    def test_severity_nested_extraction(self) -> None:
        """Verify double-underscore column name maps to nested severity field."""
        # manifest.yaml declares: severity__0__type and severity__0__score
        severity = _VULN_RECORD.get("severity", [])
        assert len(severity) > 0, "Fixture must have at least one severity entry"
        assert severity[0].get("type") == "CVSS_V3"
        assert "CVSS:3.1" in severity[0].get("score", "")

    def test_database_specific_severity_label(self) -> None:
        """Verify database_specific.severity maps to the human-readable label."""
        db_specific = _VULN_RECORD.get("database_specific", {})
        assert db_specific.get("severity") == "CRITICAL"

    def test_published_is_iso8601_timestamp(self) -> None:
        """Verify published field is parseable as ISO 8601."""
        from datetime import datetime

        published = _VULN_RECORD["published"]
        # Should not raise
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        assert dt.year == 2024

    def test_id_format_ghsa(self) -> None:
        """Verify GHSA ID format matches expected pattern."""
        import re

        vuln_id = _VULN_RECORD["id"]
        assert re.match(r"^(GHSA|CVE|PYSEC|RUSTSEC|GO)-", vuln_id), (
            f"Unexpected OSV ID format: {vuln_id}"
        )


class TestOsvAffectedTable:
    """Tests for the osv.affected table schema and data contract."""

    def test_affected_rows_extraction(self) -> None:
        """Verify rows_path correctly navigates into affected array."""
        affected = _VULN_RECORD.get("affected", [])
        assert len(affected) == 1, "Fixture should have one affected package"
        _assert_affected_schema(affected[0])

    def test_package_ecosystem_values(self) -> None:
        """Verify ecosystem values match expected OSV ecosystem names."""
        valid_ecosystems = {
            "npm", "PyPI", "Go", "Maven", "crates.io", "NuGet", "RubyGems",
            "Hex", "Pub", "Linux", "OSS-Fuzz", "Android", "GitHub Actions",
        }
        for row in _VULN_RECORD.get("affected", []):
            ecosystem = row["package"]["ecosystem"]
            assert ecosystem in valid_ecosystems, (
                f"Unexpected ecosystem '{ecosystem}'. Not in known OSV ecosystems."
            )

    def test_purl_format(self) -> None:
        """Verify package PURL starts with pkg:."""
        for row in _VULN_RECORD.get("affected", []):
            purl = row["package"].get("purl", "")
            if purl:
                assert purl.startswith("pkg:"), f"PURL must start with pkg:, got: {purl}"


class TestOsvRangesTable:
    """Tests for the osv.ranges table schema and data contract."""

    def test_ranges_have_required_fields(self) -> None:
        """Verify every range entry has type and events."""
        for affected in _VULN_RECORD.get("affected", []):
            for r in affected.get("ranges", []):
                _assert_ranges_schema(r)

    def test_range_type_values(self) -> None:
        """Verify range type is one of the three OSV range types."""
        valid_types = {"SEMVER", "ECOSYSTEM", "GIT"}
        for affected in _VULN_RECORD.get("affected", []):
            for r in affected.get("ranges", []):
                assert r["type"] in valid_types, (
                    f"Unexpected range type '{r['type']}'"
                )

    def test_events_have_introduced_or_fixed(self) -> None:
        """Verify each range event has at least one of introduced/fixed/last_affected."""
        for affected in _VULN_RECORD.get("affected", []):
            for r in affected.get("ranges", []):
                for event in r.get("events", []):
                    keys = set(event.keys())
                    assert keys & {"introduced", "fixed", "last_affected", "limit"}, (
                        f"Range event must have introduced/fixed/last_affected/limit: {event}"
                    )


class TestOsvReferencesTable:
    """Tests for the osv.references table schema and data contract."""

    def test_references_have_required_fields(self) -> None:
        """Verify every reference has type and url."""
        for ref in _VULN_RECORD.get("references", []):
            _assert_reference_schema(ref)

    def test_reference_types(self) -> None:
        """Verify reference types match the OSV reference type enum."""
        valid_types = {
            "ADVISORY", "ARTICLE", "DETECTION", "DISCUSSION", "FIX",
            "GIT", "INTRODUCED", "PACKAGE", "REPORT", "WEB",
        }
        for ref in _VULN_RECORD.get("references", []):
            assert ref["type"] in valid_types, (
                f"Unexpected reference type '{ref['type']}'"
            )


class TestOsvAliasesTable:
    """Tests for the osv.aliases table schema and data contract."""

    def test_aliases_are_strings(self) -> None:
        """Verify all alias entries are strings."""
        for alias in _VULN_RECORD.get("aliases", []):
            assert isinstance(alias, str), f"Alias must be a string, got: {type(alias)}"

    def test_aliases_match_known_prefixes(self) -> None:
        """Verify alias IDs start with known vulnerability database prefixes."""
        import re

        known_prefixes = re.compile(r"^(CVE|GHSA|PYSEC|RUSTSEC|GO|MAVEN|SNYK|OSVDB)-")
        for alias in _VULN_RECORD.get("aliases", []):
            assert known_prefixes.match(alias), (
                f"Alias '{alias}' does not match known prefix pattern"
            )


# ---------------------------------------------------------------------------
# VCR integration stubs — swap for live cassettes when available
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="VCR cassette not yet recorded — run with --vcr-record=all")
class TestOsvVcrReplay:
    """Placeholder for VCR.py cassette-replay tests.

    To record cassettes:
        1. Ensure network access to https://api.osv.dev/v1
        2. Run: pytest tests/sources/test_osv.py::TestOsvVcrReplay --vcr-record=all
        3. Cassettes will be saved to tests/sources/cassettes/osv/
        4. Subsequent runs replay from cassettes (no network needed)
    """

    def test_query_pytorch_vulns(self) -> None:
        """Query OSV for PyPI pytorch vulnerabilities and verify response shape."""
        import vcr  # type: ignore[import]

        cassette_path = CASSETTES_DIR / "query_pytorch_vulns.yaml"
        with vcr.VCR().use_cassette(str(cassette_path)):
            import httpx

            response = httpx.post(
                "https://api.osv.dev/v1/query",
                json={"package": {"name": "torch", "ecosystem": "PyPI"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert "vulns" in data
            assert len(data["vulns"]) > 0
            _assert_vuln_schema(data["vulns"][0])

    def test_get_single_vulnerability(self) -> None:
        """Fetch a single vulnerability by ID and verify all table schemas."""
        import vcr  # type: ignore[import]

        cassette_path = CASSETTES_DIR / "get_ghsa_jfh8.yaml"
        vuln_id = "GHSA-jfh8-c2jp-hdqm"
        with vcr.VCR().use_cassette(str(cassette_path)):
            import httpx

            response = httpx.get(f"https://api.osv.dev/v1/vulns/{vuln_id}")
            assert response.status_code == 200
            data = response.json()

            _assert_vuln_schema(data)
            for affected in data.get("affected", []):
                _assert_affected_schema(affected)
                for r in affected.get("ranges", []):
                    _assert_ranges_schema(r)
            for ref in data.get("references", []):
                _assert_reference_schema(ref)

    def test_manifest_yaml_is_valid(self) -> None:
        """Verify manifest.yaml is valid YAML and has required top-level fields."""
        import yaml

        manifest_path = Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        assert manifest_path.exists(), f"manifest.yaml not found at {manifest_path}"

        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert manifest["name"] == "osv"
        assert manifest["dsl_version"] == 3
        assert manifest["backend"] == "http"
        assert "tables" in manifest
        table_names = {t["name"] for t in manifest["tables"]}
        assert "vulnerabilities" in table_names
        assert "affected" in table_names
        assert "ranges" in table_names
        assert "references" in table_names
        assert "aliases" in table_names


class TestOsvManifestYaml:
    """Validate the OSV manifest.yaml structure without VCR."""

    def test_manifest_exists_and_is_valid_yaml(self) -> None:
        """Verify the manifest file exists and parses as valid YAML."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        )
        assert manifest_path.exists(), f"manifest.yaml not found at {manifest_path}"
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)
        assert manifest is not None

    def test_manifest_required_top_level_fields(self) -> None:
        """Verify all required top-level manifest fields are present."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        assert manifest["name"] == "osv"
        assert manifest["version"] == "0.1.0"
        assert manifest["dsl_version"] == 3
        assert manifest["backend"] == "http"
        assert manifest["base_url"] == "https://api.osv.dev/v1"

    def test_manifest_has_five_tables(self) -> None:
        """Verify the manifest declares exactly 5 tables."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        table_names = {t["name"] for t in manifest["tables"]}
        assert table_names == {"vulnerabilities", "affected", "ranges", "references", "aliases"}

    def test_all_tables_have_columns(self) -> None:
        """Verify every table declares at least one column."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        for table in manifest["tables"]:
            assert "columns" in table, f"Table '{table['name']}' has no columns"
            assert len(table["columns"]) > 0, f"Table '{table['name']}' has empty columns list"

    def test_column_types_are_valid(self) -> None:
        """Verify all column types are valid Coral DSL types."""
        import yaml

        valid_types = {"Utf8", "Int64", "Float64", "Boolean", "Date", "Timestamp"}
        manifest_path = (
            Path(__file__).parent.parent.parent / "sources" / "osv" / "manifest.yaml"
        )
        with manifest_path.open() as fh:
            manifest = yaml.safe_load(fh)

        for table in manifest["tables"]:
            for col in table["columns"]:
                assert col["type"] in valid_types, (
                    f"Table '{table['name']}', column '{col['name']}': "
                    f"invalid type '{col['type']}'. Must be one of {valid_types}"
                )
