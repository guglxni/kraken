import { VoyageCard } from "@/components/VoyageCard";
import { fetchRecentVoyages } from "@/lib/api";

/**
 * Captain's Bridge — home page.
 *
 * Server Component. Fetches the six most-recent voyage results at render time
 * (revalidated every 30 s) and displays them in a 3-column card grid.
 */
export default async function CaptainsBridgePage() {
  const voyages = await fetchRecentVoyages(6);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* ── Page header ──────────────────────────────────────── */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Captain&apos;s Bridge
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          One SQL query over every system you run. Recent voyages shown below.
        </p>
      </header>

      {/* ── Summary strip ────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Voyages today" value={voyages.length.toString()} />
        <StatCard
          label="Done"
          value={voyages.filter((v) => v.status === "done").length.toString()}
          accent="var(--color-green)"
        />
        <StatCard
          label="Running"
          value={voyages.filter((v) => v.status === "running").length.toString()}
          accent="var(--color-amber)"
        />
        <StatCard
          label="Failed"
          value={voyages.filter((v) => v.status === "failed").length.toString()}
          accent="var(--color-coral)"
        />
      </div>

      {/* ── Voyage grid ──────────────────────────────────────── */}
      {voyages.length === 0 ? (
        <EmptyState />
      ) : (
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-4">
            Recent Voyages
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {voyages.map((voyage) => (
              <VoyageCard key={voyage.voyage_id} voyage={voyage} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string;
  accent?: string;
}

function StatCard({ label, value, accent }: StatCardProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] px-5 py-4">
      <p className="text-xs text-[var(--color-text-muted)]">{label}</p>
      <p
        className="text-3xl font-bold mt-1"
        style={accent ? { color: accent } : { color: "var(--color-text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-[var(--color-text-muted)] text-sm max-w-sm">
        No voyages yet. Start the KRAKEN backend and run{" "}
        <code className="font-mono bg-[var(--color-border)] px-1.5 py-0.5 rounded text-xs">
          kraken run exec_escalation
        </code>{" "}
        to execute your first voyage.
      </p>
    </div>
  );
}
