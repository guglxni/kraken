"""Tests for kraken.lineage — Spyglass column-provenance extraction.

No network access required. Exercises the sqllineage primary path, the sqlglot
fallback, JSON-serializability, and the never-raise contract on malformed SQL.
"""

from __future__ import annotations

import json

from kraken.lineage import extract_lineage, format_sql, lineage_summary

_JOIN_SQL = "SELECT a.x, b.y FROM t1 a JOIN t2 b ON a.id = b.id"
_INSERT_JOIN_SQL = "INSERT INTO out SELECT a.x AS x, b.y AS y FROM t1 a JOIN t2 b ON a.id = b.id"
_MALFORMED_SQL = "SELECT FROM WHERE JOIN ;;; not valid sql at all (((("


def test_format_sql_pretty_prints() -> None:
    formatted = format_sql("select a,b from t1")
    # Pretty output should be multi-line and uppercase the SELECT keyword.
    assert "SELECT" in formatted
    assert "\n" in formatted


def test_format_sql_is_idempotent_ish() -> None:
    once = format_sql(_JOIN_SQL)
    twice = format_sql(once)
    assert once == twice


def test_format_sql_never_raises_on_garbage() -> None:
    # Garbage in → original string back out, no exception.
    result = format_sql(_MALFORMED_SQL)
    assert isinstance(result, str)


def test_extract_lineage_multi_table_join() -> None:
    result = extract_lineage(_JOIN_SQL)
    assert result["engine"] in {"sqllineage", "sqlglot"}
    assert len(result["tables"]) >= 2


def test_extract_lineage_insert_traces_columns() -> None:
    result = extract_lineage(_INSERT_JOIN_SQL)
    assert result["engine"] in {"sqllineage", "sqlglot"}
    assert len(result["tables"]) >= 2
    # An INSERT...SELECT should expose column lineage under the sqllineage engine.
    if result["engine"] == "sqllineage":
        assert len(result["columns"]) >= 1
        for col in result["columns"]:
            assert "column" in col
            assert isinstance(col["sources"], list)


def test_extract_lineage_malformed_never_raises() -> None:
    result = extract_lineage(_MALFORMED_SQL)
    assert result["engine"] in {"sqllineage", "sqlglot", "none"}
    assert isinstance(result["tables"], list)
    assert isinstance(result["columns"], list)


def test_extract_lineage_is_json_serializable() -> None:
    for sql in (_JOIN_SQL, _INSERT_JOIN_SQL, _MALFORMED_SQL):
        payload = json.dumps(extract_lineage(sql))
        assert isinstance(payload, str)


def test_extract_lineage_node_edge_shape() -> None:
    result = extract_lineage(_INSERT_JOIN_SQL)
    for node in result["nodes"]:
        assert set(node.keys()) == {"id", "label", "type"}
        assert node["type"] in {"table", "column"}
    for edge in result["edges"]:
        assert set(edge.keys()) == {"source", "target"}


def test_lineage_summary_one_line() -> None:
    summary = lineage_summary(_JOIN_SQL)
    assert "\n" not in summary
    assert "source table" in summary
    assert any(engine in summary for engine in ("sqllineage", "sqlglot", "none"))
