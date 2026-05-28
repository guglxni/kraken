"""Snapshot tests for voyage V1: Hot Deploy."""

from __future__ import annotations

import pytest

from kraken.voyages.compiler import compile_voyage, validate_voyage


def test_hot_deploy_compiles() -> None:
    compiled = compile_voyage("hot_deploy", {"deploy_sha": "abc123f"})
    assert compiled.sql is not None
    assert len(compiled.required_sources) >= 3


def test_hot_deploy_required_sources() -> None:
    compiled = compile_voyage("hot_deploy", {})
    sources = compiled.required_sources
    assert "github" in sources
    assert "sentry" in sources
    assert "datadog" in sources


def test_hot_deploy_sql_contains_deployments() -> None:
    compiled = compile_voyage("hot_deploy", {})
    assert "deployments" in compiled.sql.lower()
    assert "production" in compiled.sql.lower()


def test_hot_deploy_sql_no_select_star() -> None:
    compiled = compile_voyage("hot_deploy", {})
    for line in compiled.sql.splitlines():
        assert "SELECT *" not in line.upper(), f"Found SELECT * in: {line}"


def test_hot_deploy_validates() -> None:
    errors = validate_voyage("hot_deploy")
    assert errors == [], f"Validation errors: {errors}"


def test_hot_deploy_default_sha() -> None:
    compiled = compile_voyage("hot_deploy", {})
    assert "latest" in compiled.sql
    assert compiled.params["deploy_sha"] == "latest"
