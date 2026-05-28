import { BenchOBot } from "@/components/BenchOBot";
import { SpyglassPane } from "@/components/SpyglassPane";
import { fetchBench, fetchTrace, fetchTraces } from "@/lib/api";
import type { SpyglassTrace } from "@/lib/types";

interface SpyglassPageProps {
  searchParams: Promise<{ trace_id?: string; voyage_id?: string }>;
}

/**
 * Spyglass — SQL query trace inspector.
 *
 * Server Component. Renders the list of recent SQL traces in a sidebar and
 * displays the selected trace's full detail (SQL, plan, sources) in the main
 * pane.
 *
 * URL parameters:
 *   ?trace_id=<id>    — directly open a specific trace
 *   ?voyage_id=<id>   — show the first trace for a voyage
 */
export default async function SpyglassPage({ searchParams }: SpyglassPageProps) {
  const params = await searchParams;
  const [traces, bench] = await Promise.all([fetchTraces(20), fetchBench("exec_escalation")]);

  let selectedTrace: SpyglassTrace | null = null;

  if (params.trace_id) {
    selectedTrace = await fetchTrace(params.trace_id);
  } else if (traces.length > 0 && traces[0]) {
    // Default to the most-recent trace
    selectedTrace = traces[0];
  }

  return (
    <div className="flex h-full">
      {/* ── Trace list sidebar ─────────────────────────────── */}
      <aside className="w-72 shrink-0 border-r border-[var(--color-border)] overflow-y-auto">
        <div className="px-4 py-3 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Recent Traces</h2>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {traces.length} trace{traces.length !== 1 ? "s" : ""} available
          </p>
        </div>

        <nav className="divide-y divide-[var(--color-border)]">
          {traces.length === 0 ? (
            <p className="text-xs text-[var(--color-text-muted)] p-4">
              No traces yet. Execute a voyage to generate SQL traces.
            </p>
          ) : (
            traces.map((trace: SpyglassTrace) => (
              <TraceListItem
                key={trace.trace_id}
                trace={trace}
                isSelected={selectedTrace?.trace_id === trace.trace_id}
              />
            ))
          )}
        </nav>
      </aside>

      {/* ── Main pane ──────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto p-8">
        <h1 className="text-xl font-bold text-[var(--color-text-primary)] mb-6">Spyglass</h1>

        {bench && (
          <div className="mb-8">
            <BenchOBot bench={bench} />
          </div>
        )}

        {selectedTrace ? (
          <SpyglassPane trace={selectedTrace} />
        ) : (
          <div className="flex items-center justify-center h-64 text-[var(--color-text-muted)] text-sm">
            Select a trace from the sidebar to inspect it.
          </div>
        )}
      </main>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface TraceListItemProps {
  trace: SpyglassTrace;
  isSelected: boolean;
}

function TraceListItem({ trace, isSelected }: TraceListItemProps) {
  return (
    <a
      href={`/spyglass?trace_id=${trace.trace_id}`}
      className={`block px-4 py-3 text-xs hover:bg-[var(--color-border)] transition-colors ${
        isSelected ? "bg-[var(--color-teal)]/10 border-l-2 border-l-[var(--color-teal)]" : ""
      }`}
    >
      <div className="font-mono text-[var(--color-text-primary)] truncate">{trace.trace_id}</div>
      <div className="text-[var(--color-text-muted)] mt-0.5 truncate">{trace.voyage_id}</div>
      <div className="flex items-center gap-3 mt-1 text-[10px] text-[var(--color-text-muted)]">
        <span>{trace.duration_ms}ms</span>
        <span>{trace.row_count.toLocaleString()} rows</span>
      </div>
    </a>
  );
}
