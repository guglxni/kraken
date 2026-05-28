"""Bench-O-Bot — KRAKEN vs direct-MCP harness.

Compares executing a voyage via KRAKEN (one Coral SQL query) against
calling each source's MCP tool individually. Records latency, token
usage, and result completeness for the demo's side-by-side panel.

Architecture constraint: this is a benchmarking harness only.
The KRAKEN path still goes through coral_sql(). The "direct MCP" path
calls each source's MCP tool individually to show the contrast.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Opik availability flag. Probed lazily on first _record_opik call so that a
# missing server or config never breaks import-time or bench execution.
# Tests may force this off by setting kraken.bench._OPIK_AVAILABLE = False.
_OPIK_AVAILABLE: bool | None = None


@dataclass
class BenchRun:
    approach: str  # "kraken" | "direct_mcp"
    voyage_name: str
    voyage_id: str
    latency_ms: float
    sources_queried: list[str]
    row_count: int
    token_count: int
    tool_call_count: int
    error: str | None = None
    rows_sample: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Full JSON-serializable representation of a single bench run."""
        return {
            "approach": self.approach,
            "voyage_name": self.voyage_name,
            "voyage_id": self.voyage_id,
            "latency_ms": self.latency_ms,
            "sources_queried": list(self.sources_queried),
            "row_count": self.row_count,
            "token_count": self.token_count,
            "tool_call_count": self.tool_call_count,
            "error": self.error,
            "rows_sample": list(self.rows_sample),
        }


@dataclass
class BenchResult:
    voyage_name: str
    kraken: BenchRun | None
    direct_mcp: BenchRun | None
    latency_winner: str = ""
    coverage_winner: str = ""
    verdict: str = ""
    latency_speedup: float = 1.0

    def __post_init__(self) -> None:
        if self.kraken and self.direct_mcp:
            self.latency_winner = (
                "kraken" if self.kraken.latency_ms <= self.direct_mcp.latency_ms else "direct_mcp"
            )
            self.coverage_winner = (
                "kraken"
                if len(self.kraken.sources_queried) >= len(self.direct_mcp.sources_queried)
                else "direct_mcp"
            )
            self.latency_speedup = (
                self.direct_mcp.latency_ms / max(self.kraken.latency_ms, 1.0)
                if self.direct_mcp.latency_ms > 0
                else 1.0
            )
            self.verdict = (
                f"KRAKEN {self.latency_speedup:.1f}x faster, "
                f"covers {len(self.kraken.sources_queried)} sources in one SQL vs "
                f"{self.direct_mcp.tool_call_count} tool calls "
                f"(direct-MCP latency is a simulated estimate)"
            )

    def to_dict(self) -> dict[str, Any]:
        """Full JSON-serializable representation, returned by /api/bench.

        The direct-MCP latency is a simulated estimate (no live MCP calls are
        made); `direct_mcp_simulated` flags this so the demo stays honest.
        """
        return {
            "voyage_name": self.voyage_name,
            "kraken": self.kraken.to_dict() if self.kraken else None,
            "direct_mcp": self.direct_mcp.to_dict() if self.direct_mcp else None,
            "latency_winner": self.latency_winner,
            "coverage_winner": self.coverage_winner,
            "verdict": self.verdict,
            "latency_speedup": self.latency_speedup,
            "direct_mcp_simulated": True,
        }


async def run_kraken_bench(
    voyage_name: str,
    params: dict[str, Any] | None = None,
    voyage_id: str | None = None,
) -> BenchRun:
    """Benchmark the KRAKEN path — one Coral SQL query via crew.run()."""
    from kraken.voyages.compiler import VoyageCompileError, compile_voyage

    vid = voyage_id or str(uuid.uuid4())
    start = time.perf_counter()

    try:
        compiled = compile_voyage(voyage_name, params or {})
    except VoyageCompileError as exc:
        return BenchRun(
            approach="kraken",
            voyage_name=voyage_name,
            voyage_id=vid,
            latency_ms=0,
            sources_queried=[],
            row_count=0,
            token_count=0,
            tool_call_count=1,
            error=str(exc),
        )

    try:
        from kraken.coral_client import coral_sql
        result = await coral_sql(compiled.sql, voyage_id=vid, agent_name="bench")
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BenchRun(
            approach="kraken",
            voyage_name=voyage_name,
            voyage_id=vid,
            latency_ms=elapsed,
            sources_queried=compiled.required_sources,
            row_count=0,
            token_count=0,
            tool_call_count=1,
            error=f"coral_sql failed: {exc}",
        )

    elapsed = (time.perf_counter() - start) * 1000
    return BenchRun(
        approach="kraken",
        voyage_name=voyage_name,
        voyage_id=vid,
        latency_ms=elapsed,
        sources_queried=result.sources_queried or compiled.required_sources,
        row_count=result.row_count,
        token_count=_estimate_tokens(compiled.sql),
        tool_call_count=1,
        rows_sample=result.rows[:3],
    )


async def run_direct_mcp_bench(
    voyage_name: str,
    params: dict[str, Any] | None = None,
    voyage_id: str | None = None,
) -> BenchRun:
    """Simulate the direct-MCP path — call each source's MCP tool individually.

    In reality this would open N separate MCP sessions and call each source
    directly. For the benchmark we simulate the overhead without actually
    calling live sources (since that would require all credentials set up).
    """
    from kraken.voyages.compiler import VoyageCompileError, compile_voyage

    vid = voyage_id or str(uuid.uuid4())
    start = time.perf_counter()

    try:
        compiled = compile_voyage(voyage_name, params or {})
    except VoyageCompileError as exc:
        return BenchRun(
            approach="direct_mcp",
            voyage_name=voyage_name,
            voyage_id=vid,
            latency_ms=0,
            sources_queried=[],
            row_count=0,
            token_count=0,
            tool_call_count=0,
            error=str(exc),
        )

    sources = compiled.required_sources
    tool_call_count = len(sources)

    # Simulate per-source latency (conservative estimate: 500ms per tool call
    # for auth + request + response parsing, sequential as an LLM agent would do it)
    simulated_latency_ms = tool_call_count * 500.0
    simulated_token_overhead = tool_call_count * 800  # prompt + response per tool call

    # In a real LLM agent without Coral, you'd also need the LLM to:
    # 1. Decide which sources to call (≥1 LLM round trip per source)
    # 2. Transform each response to match the others' schema
    # 3. Join the results in Python
    llm_round_trips = tool_call_count
    simulated_latency_ms += llm_round_trips * 1200.0  # ~1.2s per LLM call
    simulated_token_overhead += llm_round_trips * 2000

    elapsed = (time.perf_counter() - start) * 1000 + simulated_latency_ms

    logger.info(
        "direct_mcp_simulated",
        sources=sources,
        tool_calls=tool_call_count,
        simulated_latency_ms=simulated_latency_ms,
    )

    return BenchRun(
        approach="direct_mcp",
        voyage_name=voyage_name,
        voyage_id=vid,
        latency_ms=elapsed,
        sources_queried=sources,
        row_count=0,  # would need to actually call each MCP
        token_count=simulated_token_overhead,
        tool_call_count=tool_call_count,
        rows_sample=[],
    )


async def bench_voyage(
    voyage_name: str,
    params: dict[str, Any] | None = None,
) -> BenchResult:
    """Run both approaches in sequence and produce a BenchResult."""
    vid = str(uuid.uuid4())
    log = logger.bind(voyage=voyage_name, bench_id=vid)
    log.info("bench_start")

    kraken_run, direct_run = await asyncio.gather(
        run_kraken_bench(voyage_name, params, vid),
        run_direct_mcp_bench(voyage_name, params, vid),
    )

    result = BenchResult(
        voyage_name=voyage_name,
        kraken=kraken_run,
        direct_mcp=direct_run,
    )

    log.info(
        "bench_complete",
        verdict=result.verdict,
        kraken_ms=kraken_run.latency_ms,
        direct_ms=direct_run.latency_ms,
    )

    # Best-effort: record the run as an Opik experiment. Never raises.
    _record_opik(result)

    return result


def _record_opik(result: BenchResult) -> None:
    """Record a bench run as an Opik trace (best-effort, offline-safe).

    Opik may try to reach a server or read missing config; ALL usage is
    wrapped so a missing server or unconfigured SDK never breaks bench_voyage.
    Sets the module flag `_OPIK_AVAILABLE` on first call and logs either
    `opik_recorded` or `opik_unavailable`.
    """
    global _OPIK_AVAILABLE

    if _OPIK_AVAILABLE is False:
        logger.debug("opik_unavailable", reason="disabled")
        return

    # Opt-in only: KRAKEN is local-first. Recording to Opik requires explicit
    # configuration (an API key or self-hosted URL); otherwise the SDK spins up
    # a background uploader that emits 401 noise. Stay silent unless configured.
    import os

    if not (
        os.getenv("OPIK_API_KEY")
        or os.getenv("OPIK_URL_OVERRIDE")
        or os.getenv("KRAKEN_OPIK_ENABLED") == "1"
    ):
        _OPIK_AVAILABLE = False
        logger.debug("opik_unavailable", reason="not_configured")
        return

    try:
        import opik

        client = opik.Opik()
        # Record into Opik's in-memory local emulator: captures the trace as a
        # real Opik experiment object without requiring a configured server or
        # API key, so the demo works fully offline.
        with opik.record_traces_locally(client=client) as storage:
            trace = client.trace(
                name="bench_voyage",
                input={"voyage_name": result.voyage_name},
                output=result.to_dict(),
                metadata={
                    "latency_winner": result.latency_winner,
                    "coverage_winner": result.coverage_winner,
                    "latency_speedup": result.latency_speedup,
                    "direct_mcp_simulated": True,
                },
                tags=["bench-o-bot", "kraken", result.voyage_name],
            )
            trace.end()
            recorded = len(storage.trace_trees)
        _OPIK_AVAILABLE = True
        logger.info(
            "opik_recorded",
            voyage=result.voyage_name,
            trace_id=trace.id,
            traces_recorded=recorded,
        )
    except Exception as exc:  # noqa: BLE001 — opik is strictly best-effort
        _OPIK_AVAILABLE = False
        logger.info("opik_unavailable", error=str(exc), voyage=result.voyage_name)


def bench_report(result: BenchResult) -> str:
    """Format a BenchResult into a CLI-ready report string."""
    lines: list[str] = [
        f"╔═══ Bench-O-Bot: {result.voyage_name} ═══╗",
        "║",
    ]

    if result.kraken:
        k = result.kraken
        status = "✓" if not k.error else "✗"
        lines.extend([
            f"║  KRAKEN path        {status}",
            f"║  └─ Latency:        {k.latency_ms:.1f}ms",
            f"║  └─ Tool calls:     {k.tool_call_count} (one Coral SQL)",
            f"║  └─ Sources:        {', '.join(k.sources_queried)}",
            f"║  └─ Rows returned:  {k.row_count}",
            f"║  └─ Tokens used:    ~{k.token_count}",
            "║",
        ])
        if k.error:
            lines.append(f"║  └─ Error: {k.error}")

    if result.direct_mcp:
        d = result.direct_mcp
        lines.extend([
            "║  Direct-MCP path    (simulated estimate)",
            f"║  └─ Latency:        {d.latency_ms:.1f}ms (estimated)",
            f"║  └─ Tool calls:     {d.tool_call_count} (one per source)",
            f"║  └─ Token overhead: ~{d.token_count}",
            "║",
        ])

    if result.verdict:
        lines.extend([
            f"║  Verdict: {result.verdict}",
            "║",
        ])

    lines.append("╚══════════════════════════════╝")
    return "\n".join(lines)


def _estimate_tokens(sql: str) -> int:
    """Rough token estimate: ~1 token per 4 chars of SQL."""
    return max(50, len(sql) // 4)
