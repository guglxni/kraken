import type { SpyglassTrace } from "@/lib/types";

interface SpyglassPaneProps {
  trace: SpyglassTrace;
}

/**
 * SpyglassPane
 *
 * Server Component. Renders the SQL text, query plan, provenance sources, and
 * execution metadata for a single Coral SQL trace.
 */
export function SpyglassPane({ trace }: SpyglassPaneProps) {
  return (
    <section className="flex flex-col gap-6">
      {/* ── Metadata row ──────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--color-text-muted)]">
        <span>
          Trace:{" "}
          <span className="font-mono text-[var(--color-text-primary)]">{trace.trace_id}</span>
        </span>
        <span>
          Voyage:{" "}
          <span className="font-mono text-[var(--color-text-primary)]">{trace.voyage_id}</span>
        </span>
        <span>
          Duration:{" "}
          <span className="font-mono text-[var(--color-text-primary)]">{trace.duration_ms}ms</span>
        </span>
        <span>
          Rows:{" "}
          <span className="font-mono text-[var(--color-text-primary)]">
            {trace.row_count.toLocaleString()}
          </span>
        </span>
        <span className="ml-auto">{new Date(trace.created_at).toLocaleString()}</span>
      </div>

      {/* ── SQL text ──────────────────────────────────────────── */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Coral SQL
        </h3>
        <pre className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-xs font-mono text-[var(--color-text-primary)] overflow-x-auto leading-relaxed whitespace-pre-wrap">
          {trace.sql}
        </pre>
      </div>

      {/* ── Query plan ────────────────────────────────────────── */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Query Plan
        </h3>
        <pre className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-xs font-mono text-[var(--color-text-muted)] overflow-x-auto leading-relaxed whitespace-pre-wrap">
          {trace.plan || "(no plan available)"}
        </pre>
      </div>

      {/* ── Source provenance ────────────────────────────────── */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Sources Queried
        </h3>
        <ul className="flex flex-wrap gap-2">
          {trace.sources.map((source) => (
            <li
              key={source}
              className="font-mono text-xs px-3 py-1 rounded-full border border-[var(--color-teal)]/40 text-[var(--color-teal)] bg-[var(--color-teal)]/5"
            >
              {source}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
