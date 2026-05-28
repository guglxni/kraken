"""Column-level SQL provenance for the Spyglass "show the receipts" view.

This module turns a rendered Coral voyage SQL string into a JSON-serializable
lineage graph (tables, columns, nodes, edges) that the Spyglass UI renders to
show which source contributed which result column.

Two engines back this module:
  1. sqllineage (PRIMARY) — full table- and column-level lineage as a graph.
  2. sqlglot (FALLBACK) — source-table extraction only when sqllineage fails.

Both libraries are optional at import time: if neither is installed the module
still imports and every function degrades gracefully (``format_sql`` returns the
input unchanged, ``extract_lineage`` returns an empty ``engine="none"`` result).
No function in this module ever raises on bad SQL.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import structlog

logger = structlog.get_logger(__name__)

# sqllineage validates against the "ansi" dialect; "duckdb" is not a supported
# sqllineage dialect, so we map the caller's DuckDB-centric dialect onto ansi.
_SQLLINEAGE_DIALECT = "ansi"

Engine = Literal["sqllineage", "sqlglot", "none"]


class ColumnLineage(TypedDict):
    """A single result column and the source columns it derives from."""

    column: str
    sources: list[str]


class GraphNode(TypedDict):
    """A node in the lineage graph (a table or a column)."""

    id: str
    label: str
    type: Literal["table", "column"]


class GraphEdge(TypedDict):
    """A directed edge from a source node to a target node."""

    source: str
    target: str


class LineageResult(TypedDict):
    """The complete, JSON-serializable lineage payload for Spyglass."""

    tables: list[str]
    columns: list[ColumnLineage]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    engine: Engine


def format_sql(sql: str, dialect: str = "duckdb") -> str:
    """Pretty-print SQL via sqlglot, falling back to the original on any error.

    Args:
        sql: The raw SQL string to format.
        dialect: The SQL dialect to read and write (defaults to DuckDB).

    Returns:
        The pretty-printed SQL, or the original ``sql`` unchanged if sqlglot is
        not installed or fails to parse the statement. Never raises.
    """
    try:
        import sqlglot  # type: ignore[import-untyped]

        formatted = sqlglot.transpile(sql, read=dialect, write=dialect, pretty=True)
        if formatted:
            return formatted[0]
        return sql
    except ImportError:
        logger.debug("format_sql_no_sqlglot")
        return sql
    except Exception as exc:  # noqa: BLE001 — formatting must never raise
        logger.debug("format_sql_failed", error=str(exc))
        return sql


def _empty_result(engine: Engine) -> LineageResult:
    """Return an empty lineage payload tagged with the given engine."""
    return {
        "tables": [],
        "columns": [],
        "nodes": [],
        "edges": [],
        "engine": engine,
    }


def _build_runner(sql: str) -> Any:
    """Construct a sqllineage LineageRunner, tolerant of dialect support.

    Tries the ansi dialect first; if that is rejected by this sqllineage
    version, falls back to a non-validating runner, then to a bare runner.
    Returns the runner instance.
    """
    from sqllineage.runner import LineageRunner  # type: ignore[import-untyped]

    for dialect in (_SQLLINEAGE_DIALECT, "non_validating"):
        try:
            return LineageRunner(sql, dialect=dialect)
        except Exception:  # noqa: BLE001 — try the next dialect option
            continue
    # Final attempt: let sqllineage pick its own default.
    return LineageRunner(sql)


def _source_tables(runner: Any) -> list[str]:
    """Read source tables from a runner, handling both property and method APIs.

    Across sqllineage versions ``source_tables`` is exposed either as a cached
    property (a list) or as a callable method. Handle both transparently.
    """
    attr = runner.source_tables
    tables = attr() if callable(attr) else attr
    return [str(t) for t in tables]


def _extract_with_sqllineage(sql: str) -> LineageResult | None:
    """Run the primary sqllineage path. Returns None if the engine is unusable."""
    try:
        runner = _build_runner(sql)
        tables = _source_tables(runner)
        column_paths = runner.get_column_lineage()
    except ImportError:
        return None
    except Exception as exc:  # noqa: BLE001 — fall back to sqlglot on any failure
        logger.debug("sqllineage_failed", error=str(exc))
        return None

    columns: list[ColumnLineage] = []
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    seen_edges: set[tuple[str, str]] = set()

    for table in tables:
        nodes.setdefault(table, {"id": table, "label": table, "type": "table"})

    for path in column_paths:
        if not path:
            continue
        source_col = str(path[0])
        target_col = str(path[-1])

        nodes.setdefault(source_col, {"id": source_col, "label": source_col, "type": "column"})
        nodes.setdefault(target_col, {"id": target_col, "label": target_col, "type": "column"})

        columns.append({"column": target_col, "sources": [source_col]})

        edge_key = (source_col, target_col)
        if source_col != target_col and edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({"source": source_col, "target": target_col})

    return {
        "tables": tables,
        "columns": columns,
        "nodes": list(nodes.values()),
        "edges": edges,
        "engine": "sqllineage",
    }


def _extract_with_sqlglot(sql: str, dialect: str) -> LineageResult | None:
    """Fallback path: extract only source tables via sqlglot. None on failure."""
    try:
        import sqlglot  # type: ignore[import-untyped]
        from sqlglot import exp

        parsed = sqlglot.parse_one(sql, dialect=dialect)
    except ImportError:
        return None
    except Exception as exc:  # noqa: BLE001 — fall through to the empty result
        logger.debug("sqlglot_fallback_failed", error=str(exc))
        return None

    tables: list[str] = []
    seen: set[str] = set()
    for table in parsed.find_all(exp.Table):
        name = table.name
        if name and name not in seen:
            seen.add(name)
            tables.append(name)

    nodes: list[GraphNode] = [{"id": t, "label": t, "type": "table"} for t in tables]
    return {
        "tables": tables,
        "columns": [],
        "nodes": nodes,
        "edges": [],
        "engine": "sqlglot",
    }


def extract_lineage(sql: str, dialect: str = "duckdb") -> dict[str, Any]:
    """Extract a JSON-serializable column-provenance graph from a SQL string.

    Tries sqllineage first (table + column lineage), falls back to sqlglot
    (source tables only), and finally returns an empty ``engine="none"`` result.
    Never raises.

    Args:
        sql: The rendered voyage SQL to analyze.
        dialect: The SQL dialect used for the sqlglot fallback path.

    Returns:
        A dict matching :class:`LineageResult` with keys ``tables``, ``columns``,
        ``nodes``, ``edges`` and ``engine``.
    """
    result = _extract_with_sqllineage(sql)
    if result is None:
        result = _extract_with_sqlglot(sql, dialect)
    if result is None:
        result = _empty_result("none")

    logger.info(
        "lineage_extracted",
        engine=result["engine"],
        tables=len(result["tables"]),
        columns=len(result["columns"]),
    )
    return result


def lineage_summary(sql: str) -> str:
    """Return a one-line human summary of a SQL statement's lineage.

    Example: ``"2 source tables, 2 columns traced via sqllineage"``.
    """
    result = extract_lineage(sql)
    n_tables = len(result["tables"])
    n_columns = len(result["columns"])
    table_word = "table" if n_tables == 1 else "tables"
    column_word = "column" if n_columns == 1 else "columns"
    return (
        f"{n_tables} source {table_word}, {n_columns} {column_word} traced via {result['engine']}"
    )
