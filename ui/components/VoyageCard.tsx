import type { VoyageResult } from "@/lib/types";

interface VoyageCardProps {
  voyage: VoyageResult;
}

const STATUS_STYLES: Record<VoyageResult["status"], string> = {
  done: "bg-[var(--color-green)]/10 text-[var(--color-green)] border-[var(--color-green)]/30",
  running:
    "bg-[var(--color-amber)]/10 text-[var(--color-amber)] border-[var(--color-amber)]/30",
  failed:
    "bg-[var(--color-coral)]/10 text-[var(--color-coral)] border-[var(--color-coral)]/30",
  pending:
    "bg-[var(--color-text-muted)]/10 text-[var(--color-text-muted)] border-[var(--color-text-muted)]/30",
};

const STATUS_LABELS: Record<VoyageResult["status"], string> = {
  done: "Complete",
  running: "Running",
  failed: "Failed",
  pending: "Pending",
};

/** Formats an ISO timestamp as a human-readable relative time label. */
function relativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

/**
 * VoyageCard
 *
 * A Server Component card displaying the status, metrics, and source list for
 * a single voyage result. Intended for use in a grid on the Captain's Bridge.
 */
export function VoyageCard({ voyage }: VoyageCardProps) {
  const statusStyle = STATUS_STYLES[voyage.status];
  const statusLabel = STATUS_LABELS[voyage.status];

  return (
    <article className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] p-5 flex flex-col gap-4 hover:border-[var(--color-teal)]/50 transition-colors">
      {/* Header ─────────────────────────────────────────────── */}
      <header className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-[var(--color-text-primary)] text-sm leading-snug">
          {voyage.name}
        </h3>
        <span
          className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full border ${statusStyle}`}
        >
          {statusLabel}
        </span>
      </header>

      {/* Metrics ────────────────────────────────────────────── */}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <div>
          <dt className="text-[var(--color-text-muted)]">Rows</dt>
          <dd className="font-mono font-semibold text-[var(--color-text-primary)]">
            {voyage.row_count.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Latency</dt>
          <dd className="font-mono font-semibold text-[var(--color-text-primary)]">
            {voyage.latency_ms}ms
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-[var(--color-text-muted)]">Executed</dt>
          <dd className="text-[var(--color-text-primary)]">
            {relativeTime(voyage.created_at)}
          </dd>
        </div>
      </dl>

      {/* Sources ────────────────────────────────────────────── */}
      <footer className="flex flex-wrap gap-1.5">
        {voyage.sources_queried.map((source) => (
          <span
            key={source}
            className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--color-border)] text-[var(--color-text-muted)]"
          >
            {source}
          </span>
        ))}
      </footer>

      {/* CTA ────────────────────────────────────────────────── */}
      <a
        href={`/spyglass?voyage_id=${voyage.voyage_id}`}
        className="text-xs text-[var(--color-teal)] hover:text-[var(--color-text-primary)] transition-colors mt-auto self-start"
      >
        Inspect in Spyglass →
      </a>
    </article>
  );
}
