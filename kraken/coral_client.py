"""Coral MCP stdio client — the ONLY data path for reads in KRAKEN.

Every agent read goes through coral_sql(). No direct source API imports.
The MCP tool name is `sql` (not coral_sql) — Coral v0.4.x exposes:
  - sql: Execute read-only SQL against the Coral database
  - list_catalog: List database tables with pagination
  - search_catalog: Search catalog metadata with Rust regex
  - describe_table: Show compact metadata for one table
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from kraken.models import ResultSet

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("kraken.coral")

# Coral CLI command — spawned as a subprocess via MCP stdio transport
_CORAL_CMD = "coral"
_CORAL_ARGS = ["mcp-stdio"]


@asynccontextmanager
async def _coral_session() -> AsyncIterator[ClientSession]:
    """Open a fresh MCP stdio session to the Coral subprocess."""
    server_params = StdioServerParameters(
        command=_CORAL_CMD,
        args=_CORAL_ARGS,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def coral_sql(
    query: str,
    voyage_id: str,
    agent_name: str = "unknown",
) -> ResultSet:
    """Execute a SQL query against Coral's federated sources.

    This is the single entry point for all data access in KRAKEN.
    Every call is wrapped in an OpenTelemetry span.

    Args:
        query: SQL query text (Coral dialect, DuckDB-compatible)
        voyage_id: Correlation ID for the active voyage
        agent_name: Name of the calling agent (for observability)

    Returns:
        ResultSet with rows, row_count, cache_hit, latency_ms, sources_queried

    Raises:
        CoralQueryError: On any Coral execution failure (query text included)
    """
    with tracer.start_as_current_span("coral.sql") as span:
        span.set_attribute("voyage.id", voyage_id)
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("coral.sql.text", query[:500])

        start = time.monotonic()
        try:
            async with _coral_session() as session:
                result = await session.call_tool("sql", {"query": query})

            elapsed_ms = (time.monotonic() - start) * 1000

            # Parse Coral's tool result into our ResultSet model
            result_set = _parse_coral_result(result, elapsed_ms)

            span.set_attribute("coral.sql.row_count", result_set.row_count)
            span.set_attribute("coral.sql.cache_hit", result_set.cache_hit)
            span.set_attribute("coral.sql.latency_ms", elapsed_ms)
            span.set_attribute(
                "coral.sql.sources", ",".join(result_set.sources_queried)
            )
            span.set_status(Status(StatusCode.OK))

            logger.info(
                "coral_sql_ok",
                voyage_id=voyage_id,
                agent=agent_name,
                rows=result_set.row_count,
                latency_ms=round(elapsed_ms, 1),
                cache_hit=result_set.cache_hit,
            )
            return result_set

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            logger.error(
                "coral_sql_error",
                voyage_id=voyage_id,
                agent=agent_name,
                query=query[:200],
                error=str(exc),
                latency_ms=round(elapsed_ms, 1),
            )
            raise CoralQueryError(query=query, cause=exc) from exc


async def coral_list_catalog(
    voyage_id: str,
    page: int = 1,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """List all tables available in the Coral catalog."""
    async with _coral_session() as session:
        result = await session.call_tool(
            "list_catalog", {"page": page, "page_size": page_size}
        )
    return _extract_content(result)


async def coral_describe_table(table_name: str, voyage_id: str) -> dict[str, Any]:
    """Show compact metadata for a single Coral table."""
    async with _coral_session() as session:
        result = await session.call_tool("describe_table", {"table": table_name})
    return _extract_content(result)


def _parse_coral_result(raw: Any, latency_ms: float) -> ResultSet:
    """Convert Coral MCP tool result to a typed ResultSet."""
    content = _extract_content(raw)

    if isinstance(content, list):
        rows = content
    elif isinstance(content, dict) and "rows" in content:
        rows = content["rows"]
    else:
        rows = []

    return ResultSet(
        rows=rows,
        row_count=len(rows),
        cache_hit=bool(getattr(raw, "cache_hit", False)),
        latency_ms=latency_ms,
        sources_queried=getattr(raw, "sources", []),
    )


def _extract_content(raw: Any) -> Any:
    """Extract the actual content from an MCP CallToolResult."""
    if hasattr(raw, "content"):
        content = raw.content
        if isinstance(content, list) and content:
            first = content[0]
            if hasattr(first, "text"):
                import json
                try:
                    return json.loads(first.text)
                except (json.JSONDecodeError, TypeError):
                    return first.text
        return content
    return raw


class CoralQueryError(Exception):
    """Raised when a Coral SQL query fails. Always includes query text."""

    def __init__(self, query: str, cause: Exception) -> None:
        self.query = query
        self.cause = cause
        super().__init__(f"Coral query failed: {cause}\nQuery: {query[:300]}")
