"""Tests for Bench-O-Bot (kraken/bench.py).

Covers the public interface (bench_voyage, BenchResult/BenchRun, to_dict),
JSON serialization for the future /api/bench endpoint, and the guarantee that
Opik being unavailable never breaks a bench run.

coral_sql is not available without a live Coral connection; run_kraken_bench
already catches the failure and returns a BenchRun with an `error` set, so we
assert gracefully rather than mocking a live backend.
"""

from __future__ import annotations

import json

import pytest

import kraken.bench as bench
from kraken.bench import BenchResult, BenchRun, bench_report, bench_voyage


async def test_bench_voyage_returns_result_with_both_runs() -> None:
    result = await bench_voyage("exec_escalation")

    assert isinstance(result, BenchResult)
    assert result.voyage_name == "exec_escalation"
    assert result.kraken is not None
    assert result.direct_mcp is not None
    assert isinstance(result.kraken, BenchRun)
    assert isinstance(result.direct_mcp, BenchRun)
    # Verdict is populated whenever both runs are present.
    assert result.verdict != ""
    assert result.latency_winner in {"kraken", "direct_mcp"}
    assert result.coverage_winner in {"kraken", "direct_mcp"}


async def test_bench_report_renders() -> None:
    result = await bench_voyage("exec_escalation")
    report = bench_report(result)
    assert "Bench-O-Bot" in report
    assert "exec_escalation" in report
    assert "simulated" in report.lower()


async def test_to_dict_is_json_serializable_and_complete() -> None:
    result = await bench_voyage("exec_escalation")
    payload = result.to_dict()

    # Must round-trip through JSON cleanly for the HTTP API.
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["voyage_name"] == "exec_escalation"
    assert "latency_speedup" in decoded
    assert isinstance(decoded["latency_speedup"], float)
    assert decoded["direct_mcp_simulated"] is True
    assert decoded["verdict"] != ""
    assert decoded["latency_winner"] in {"kraken", "direct_mcp"}
    assert decoded["coverage_winner"] in {"kraken", "direct_mcp"}

    # Both nested runs serialize fully.
    for key in ("kraken", "direct_mcp"):
        run = decoded[key]
        assert run is not None
        for field_name in (
            "approach",
            "voyage_name",
            "voyage_id",
            "latency_ms",
            "sources_queried",
            "row_count",
            "token_count",
            "tool_call_count",
            "error",
            "rows_sample",
        ):
            assert field_name in run


def test_benchrun_to_dict_round_trips() -> None:
    run = BenchRun(
        approach="kraken",
        voyage_name="demo",
        voyage_id="abc-123",
        latency_ms=12.5,
        sources_queried=["gmail", "sentry"],
        row_count=3,
        token_count=200,
        tool_call_count=1,
        rows_sample=[{"id": 1}],
    )
    d = run.to_dict()
    assert json.loads(json.dumps(d)) == {
        "approach": "kraken",
        "voyage_name": "demo",
        "voyage_id": "abc-123",
        "latency_ms": 12.5,
        "sources_queried": ["gmail", "sentry"],
        "row_count": 3,
        "token_count": 200,
        "tool_call_count": 1,
        "error": None,
        "rows_sample": [{"id": 1}],
    }


async def test_opik_unavailable_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the Opik path off; bench_voyage must still succeed.
    monkeypatch.setattr(bench, "_OPIK_AVAILABLE", False)
    result = await bench_voyage("exec_escalation")
    assert isinstance(result, BenchResult)
    assert result.kraken is not None


def test_record_opik_never_raises_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bench, "_OPIK_AVAILABLE", False)
    result = BenchResult(
        voyage_name="demo",
        kraken=BenchRun("kraken", "demo", "v", 10.0, ["a"], 1, 50, 1),
        direct_mcp=BenchRun("direct_mcp", "demo", "v", 100.0, ["a"], 0, 800, 1),
    )
    # Should be a no-op that does not raise.
    bench._record_opik(result)


def test_latency_speedup_computed() -> None:
    result = BenchResult(
        voyage_name="demo",
        kraken=BenchRun("kraken", "demo", "v", 10.0, ["a", "b"], 1, 50, 1),
        direct_mcp=BenchRun("direct_mcp", "demo", "v", 100.0, ["a", "b"], 0, 800, 2),
    )
    assert result.latency_speedup == pytest.approx(10.0)
    assert result.to_dict()["latency_speedup"] == pytest.approx(10.0)
