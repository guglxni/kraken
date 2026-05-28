import type { BenchResult, BenchSide } from "@/lib/types";
import { BarList, Card } from "@tremor/react";

interface BenchOBotProps {
  bench: BenchResult;
}

/**
 * BenchOBot
 *
 * Server Component. Renders a side-by-side comparison of the KRAKEN (Coral SQL)
 * approach versus the direct-MCP approach for a single voyage, surfacing
 * latency, tool-call count, sources covered, and token usage. The direct-MCP
 * column is labelled "(estimated)" when its numbers are simulated.
 */
export function BenchOBot({ bench }: BenchOBotProps) {
  const { kraken, direct_mcp, direct_mcp_simulated } = bench;

  const directLabel = direct_mcp_simulated ? "Direct MCP (estimated)" : "Direct MCP";

  return (
    <Card className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] p-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Bench-O-Bot</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Coral SQL vs direct MCP for{" "}
            <code className="font-mono bg-[var(--color-border)] px-1 rounded">
              {bench.voyage_name}
            </code>
          </p>
        </div>
        {bench.latency_speedup > 0 && (
          <span className="shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full border border-[var(--color-teal)]/40 bg-[var(--color-teal)]/10 text-[var(--color-teal)]">
            {bench.latency_speedup.toFixed(1)}× faster
          </span>
        )}
      </div>

      {/* ── Metric comparison grid ────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">
        <BenchColumn label="KRAKEN (Coral)" side={kraken} accent="var(--color-teal)" />
        <BenchColumn label={directLabel} side={direct_mcp} accent="var(--color-coral)" />
      </div>

      {/* ── Latency bar comparison ────────────────────────────── */}
      <div className="mt-5">
        <h4 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Latency (ms)
        </h4>
        <BarList
          data={[
            { name: "KRAKEN (Coral)", value: kraken.latency_ms, color: "teal" },
            { name: directLabel, value: direct_mcp.latency_ms, color: "rose" },
          ]}
          valueFormatter={(v: number) => `${v.toLocaleString()} ms`}
          className="text-xs"
        />
      </div>

      {/* ── Tool-call bar comparison ──────────────────────────── */}
      <div className="mt-4">
        <h4 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Tool calls
        </h4>
        <BarList
          data={[
            { name: "KRAKEN (Coral)", value: kraken.tool_call_count, color: "teal" },
            { name: directLabel, value: direct_mcp.tool_call_count, color: "rose" },
          ]}
          valueFormatter={(v: number) => v.toLocaleString()}
          className="text-xs"
        />
      </div>

      {/* ── Verdict ───────────────────────────────────────────── */}
      <div className="mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <p className="text-xs text-[var(--color-text-primary)] leading-relaxed">{bench.verdict}</p>
        <div className="flex flex-wrap gap-3 mt-2 text-[10px] text-[var(--color-text-muted)]">
          <span>
            Latency winner:{" "}
            <span className="font-mono text-[var(--color-teal)]">{bench.latency_winner}</span>
          </span>
          <span>
            Coverage winner:{" "}
            <span className="font-mono text-[var(--color-teal)]">{bench.coverage_winner}</span>
          </span>
        </div>
      </div>
    </Card>
  );
}

interface BenchColumnProps {
  label: string;
  side: BenchSide;
  accent: string;
}

function BenchColumn({ label, side, accent }: BenchColumnProps) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-xs font-semibold mb-3" style={{ color: accent }}>
        {label}
      </p>
      <dl className="space-y-2 text-xs">
        <Metric label="Latency" value={`${side.latency_ms.toLocaleString()} ms`} />
        <Metric label="Tool calls" value={side.tool_call_count.toLocaleString()} />
        <Metric label="Sources" value={side.sources_queried.length.toLocaleString()} />
        <Metric label="Tokens" value={side.token_count.toLocaleString()} />
        <Metric label="Rows" value={side.row_count.toLocaleString()} />
      </dl>
      {side.error && (
        <p className="mt-3 text-[10px] text-[var(--color-coral)]">Error: {side.error}</p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <dt className="text-[var(--color-text-muted)]">{label}</dt>
      <dd className="font-mono font-semibold text-[var(--color-text-primary)]">{value}</dd>
    </div>
  );
}
