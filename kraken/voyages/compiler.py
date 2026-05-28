"""Compile voyage YAML + params into executable SQL via Jinja2.

Supports two SQL storage formats:
  1. Inline SQL in the YAML file under the `sql:` key (existing format).
  2. External Jinja2 template in a `.sql.j2` file alongside the YAML (spec format).
     Specify `sql: voyage_name.sql.j2` in the YAML to use this format.

Jinja2 templates use `{{ param_name }}` (flat namespace) for external .sql.j2 files
and `{{ params.param_name }}` (namespaced) for inline SQL blocks to preserve backward
compatibility with the existing voyages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
import yaml
from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError

from kraken.models import CompiledVoyage

logger = structlog.get_logger(__name__)

_VOYAGES_DIR = Path(__file__).parent


class VoyageCompileError(Exception):
    """Raised when a voyage fails to compile. Message always includes voyage name."""


def _resolve_sql_template(spec: dict[str, Any], voyage_path: Path) -> str:
    """Return the raw SQL template string from spec.

    Handles both inline SQL blocks and external .sql.j2 file references.
    """
    sql_field = spec.get("sql", "")

    # External .sql.j2 file reference
    if isinstance(sql_field, str) and sql_field.strip().endswith(".j2"):
        j2_path = voyage_path.parent / sql_field.strip()
        if not j2_path.exists():
            raise VoyageCompileError(
                f"External SQL template not found: {j2_path} "
                f"(referenced from {voyage_path})"
            )
        return j2_path.read_text()

    # Inline SQL block (string in YAML)
    if isinstance(sql_field, str):
        return sql_field

    raise VoyageCompileError(
        f"Voyage '{spec.get('name', '?')}' has invalid 'sql' field — "
        "must be an inline SQL string or a path ending in .j2"
    )


def compile_voyage(name: str, params: dict[str, Any]) -> CompiledVoyage:
    """Load voyage YAML and render its SQL with the provided params.

    Normalises the voyage name: both 'hot_deploy' and 'hot-deploy' resolve to
    the same file (underscores and hyphens are interchangeable in voyage names).
    """
    # Normalise separators: allow both hot-deploy and hot_deploy as input
    normalised = name.replace("-", "_")
    path = _VOYAGES_DIR / f"{normalised}.yaml"
    if not path.exists():
        # Try with hyphens (file might be stored either way)
        path = _VOYAGES_DIR / f"{name.replace('_', '-')}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in _VOYAGES_DIR.glob("*.yaml"))
        raise VoyageCompileError(
            f"Unknown voyage '{name}'. Available: {', '.join(available)}"
        )

    try:
        spec = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise VoyageCompileError(f"Failed to parse {path}: {exc}") from exc

    # Merge provided params with defaults from spec
    # Supports both list-of-dicts (spec format) and dict-of-dicts (existing format)
    param_defs_raw = spec.get("params", {}) or {}
    param_defs: dict[str, dict[str, Any]]
    if isinstance(param_defs_raw, list):
        # New spec format: list of {name, type, default, description}
        param_defs = {item["name"]: item for item in param_defs_raw}
    else:
        # Existing format: dict of {param_name: {type, default, description}}
        param_defs = param_defs_raw

    merged: dict[str, Any] = {}
    for param_name, param_def in param_defs.items():
        if param_name in params:
            merged[param_name] = params[param_name]
        elif "default" in param_def:
            merged[param_name] = param_def["default"]
        else:
            raise VoyageCompileError(
                f"Voyage '{name}' requires param '{param_name}' (no default provided)"
            )

    sql_template = _resolve_sql_template(spec, path)

    # Detect template namespace: external .j2 files use flat {{ param_name }},
    # inline SQL blocks use {{ params.param_name }} for backward compatibility.
    sql_field = spec.get("sql", "")
    is_external_j2 = isinstance(sql_field, str) and sql_field.strip().endswith(".j2")

    render_context: dict[str, Any]
    if is_external_j2:
        # Flat namespace: {{ hours_back }}, {{ mrr_threshold }}, etc.
        render_context = merged
    else:
        # Namespaced: {{ params.hours_back }}, {{ params.mrr_threshold }}, etc.
        render_context = {"params": merged}

    try:
        env = Environment(undefined=StrictUndefined)
        rendered_sql = env.from_string(sql_template).render(**render_context)
    except UndefinedError as exc:
        raise VoyageCompileError(
            f"Voyage '{name}' SQL template references undefined variable: {exc}"
        ) from exc
    except TemplateError as exc:
        raise VoyageCompileError(
            f"Voyage '{name}' SQL template render error: {exc}"
        ) from exc

    # Normalise output_schema: handle both list-of-dicts and flat list
    output_schema_raw = spec.get("output_schema", [])
    output_schema: list[dict[str, str]]
    if output_schema_raw and isinstance(output_schema_raw[0], dict):
        output_schema = [
            {"name": item.get("name", ""), "type": item.get("type", "string")}
            for item in output_schema_raw
        ]
    else:
        output_schema = output_schema_raw  # type: ignore[assignment]

    logger.debug(
        "voyage_compiled",
        voyage=name,
        params=list(merged.keys()),
        sources=spec.get("required_sources", []),
        sql_lines=rendered_sql.count("\n"),
    )

    return CompiledVoyage(
        name=spec["name"],
        sql=rendered_sql,
        required_sources=spec.get("required_sources", []),
        params=merged,
        output_schema=output_schema,
    )


def list_voyages() -> list[dict[str, Any]]:
    """Return summary metadata for all registered voyages."""
    voyages = []
    for path in sorted(_VOYAGES_DIR.glob("*.yaml")):
        try:
            spec = yaml.safe_load(path.read_text())
            if not isinstance(spec, dict) or "name" not in spec:
                continue
            voyages.append({
                "name": spec["name"],
                "version": spec.get("version", ""),
                "description": str(spec.get("description", "")).strip(),
                "required_sources": spec.get("required_sources", []),
                "target_agent": spec.get("target_agent"),
            })
        except (yaml.YAMLError, KeyError):
            pass
    return voyages


def validate_voyage(name: str) -> list[str]:
    """Validate a voyage YAML. Returns list of validation error strings (empty = OK).

    Checks:
    - Required YAML fields are present
    - SQL template is resolvable
    - SQL contains no SELECT *
    - SQL has a LIMIT clause
    - At least 3 required_sources listed
    - sqlglot can parse the rendered SQL (structural validation)
    """
    normalised = name.replace("-", "_")
    path = _VOYAGES_DIR / f"{normalised}.yaml"
    if not path.exists():
        path = _VOYAGES_DIR / f"{name.replace('_', '-')}.yaml"
    if not path.exists():
        return [f"File not found: {_VOYAGES_DIR / normalised}.yaml"]

    errors: list[str] = []
    try:
        spec = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        return [f"YAML parse error: {exc}"]

    required_fields = ["name", "version", "description", "required_sources"]
    for field in required_fields:
        if field not in spec:
            errors.append(f"Missing required field: '{field}'")

    # Must have either inline sql or a sql.j2 reference
    if "sql" not in spec:
        errors.append("Missing required field: 'sql'")
    else:
        try:
            sql_template = _resolve_sql_template(spec, path)
        except VoyageCompileError as exc:
            errors.append(str(exc))
            return errors

        # Basic SQL quality checks (on raw template, before rendering)
        sql_upper = sql_template.upper()
        if re.search(r"\bSELECT\s+\*", sql_upper):
            errors.append("SQL contains SELECT * — name every column explicitly")
        if "LIMIT" not in sql_upper:
            errors.append("SQL missing LIMIT clause — all voyage queries must be bounded")

        # Attempt sqlglot parse on a stub-rendered version.
        # Two-pass substitution:
        #   1. '{{ ... }}' — template vars directly surrounded by SQL string quotes
        #      → replace the entire quoted expression with '_stub_'
        #   2. Remaining {{ ... }} (unquoted numeric/identifier positions) → replace with 1
        # Use a tight adjacent-match regex (no [^']* spans) to avoid cross-boundary matches.
        stub_sql = re.sub(r"'\s*\{\{[^}]+\}\}\s*'", "'_stub_'", sql_template)
        stub_sql = re.sub(r"\{\{[^}]+\}\}", "1", stub_sql)
        try:
            import sqlglot  # type: ignore[import-untyped]
            sqlglot.parse(stub_sql, dialect="duckdb")
        except ImportError:
            pass  # sqlglot not installed — skip structural SQL validation
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sqlglot parse error (stub render): {exc}")

    source_count = len(spec.get("required_sources", []))
    if source_count < 3:
        errors.append(
            f"Voyage declares only {source_count} required_source(s) — "
            "voyages must JOIN at least 3 Coral sources"
        )

    return errors
