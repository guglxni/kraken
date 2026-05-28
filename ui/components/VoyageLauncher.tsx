"use client";

import { VoyageChart } from "@/components/VoyageChart";
import type { SseEvent, VoyageDef } from "@/lib/api";
import { streamVoyage } from "@/lib/api";
import { useCallback, useRef, useState } from "react";

type Phase = "idle" | "compiled" | "executing" | "done" | "error";

interface StreamState {
  phase: Phase;
  agent?: string;
  sources?: string[];
  rows?: Record<string, unknown>[];
  rowCount?: number;
  latencyMs?: number;
  error?: string;
}

interface VoyageLauncherProps {
  voyage: VoyageDef;
}

export function VoyageLauncher({ voyage }: VoyageLauncherProps) {
  const [state, setState] = useState<StreamState>({ phase: "idle" });
  const cancelRef = useRef<(() => void) | null>(null);

  const run = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    setState({ phase: "compiled" });

    cancelRef.current = streamVoyage(voyage.name, {}, (ev: SseEvent) => {
      switch (ev.event) {
        case "compiled":
          setState((s) => ({ ...s, phase: "compiled", sources: ev.data.sources }));
          break;
        case "executing":
          setState((s) => ({ ...s, phase: "executing", agent: ev.data.target_agent }));
          break;
        case "finding":
          setState((s) => ({
            ...s,
            phase: "done",
            rows: ev.data.rows,
            rowCount: ev.data.row_count,
            latencyMs: ev.data.latency_ms,
            sources: ev.data.sources_queried ?? s.sources,
          }));
          break;
        case "done":
          setState((s) => ({ ...s, phase: "done" }));
          break;
        case "error":
          setState((s) => ({ ...s, phase: "error", error: ev.data.error }));
          break;
      }
    });
  }, [voyage.name]);

  const reset = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    setState({ phase: "idle" });
  }, []);

  const { phase, agent, sources, rows, rowCount, latencyMs, error } = state;
  const isRunning = phase === "compiled" || phase === "executing";

  return (
    <div className="flex flex-col gap-3">
      {/* ── Action bar ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={phase === "idle" ? run : reset}
          disabled={isRunning}
          className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors border
            ${
              isRunning
                ? "border-[var(--color-border)] text-[var(--color-text-muted)] cursor-wait"
                : phase === "done" || phase === "error"
                  ? "border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                  : "border-[var(--color-teal)] text-[var(--color-teal)] hover:bg-[var(--color-teal)]/10"
            }`}
        >
          {isRunning ? "Running…" : phase === "idle" ? "Run" : "Reset"}
        </button>

        {/* Phase indicator */}
        {phase !== "idle" && (
          <span className="text-xs text-[var(--color-text-muted)] font-mono">
            {phase === "compiled" && "compiling SQL…"}
            {phase === "executing" && `dispatching → ${agent ?? "agent"}`}
            {phase === "done" && `done · ${latencyMs?.toFixed(0) ?? "?"}ms`}
            {phase === "error" && "error"}
          </span>
        )}
      </div>

      {/* ── Source badges ──────────────────────────────────────── */}
      {sources && sources.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {sources.map((s) => (
            <span
              key={s}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--color-teal)]/10 text-[var(--color-teal)] border border-[var(--color-teal)]/20"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────────── */}
      {phase === "error" && error && (
        <p className="text-xs text-[var(--color-coral)] font-mono">{error}</p>
      )}

      {/* ── Chart + results table ─────────────────────────────── */}
      {phase === "done" && rows && rows.length > 0 && (
        <>
          <VoyageChart voyageName={voyage.name} rows={rows} />
          <ResultsTable rows={rows} rowCount={rowCount ?? rows.length} />
        </>
      )}
    </div>
  );
}

// ─── Results table ────────────────────────────────────────────────────────────

function ResultsTable({
  rows,
  rowCount,
}: {
  rows: Record<string, unknown>[];
  rowCount: number;
}) {
  const columns = Object.keys(rows[0] ?? {});

  return (
    <div className="overflow-x-auto rounded-md border border-[var(--color-border)]">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-raise)]">
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left font-medium text-[var(--color-text-muted)] font-mono whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[var(--color-border)]/50 last:border-0 hover:bg-[var(--color-surface-raise)]/50"
            >
              {columns.map((col) => (
                <td
                  key={col}
                  className="px-3 py-2 font-mono text-[var(--color-text-primary)] whitespace-nowrap max-w-[200px] truncate"
                  title={String(row[col] ?? "")}
                >
                  {formatCell(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rowCount > rows.length && (
        <p className="px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] border-t border-[var(--color-border)]">
          Showing {rows.length} of {rowCount} rows
        </p>
      )}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}
