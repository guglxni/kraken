import { VoyageLauncher } from "@/components/VoyageLauncher";
import { fetchHealth, fetchVoyageDefs } from "@/lib/api";
import type { VoyageDef } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CaptainsBridgePage() {
  const [health, voyageDefs] = await Promise.all([fetchHealth(), fetchVoyageDefs()]);
  const isDemoMode = health?.demo_mode === true;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* ── Demo mode banner ─────────────────────────────────── */}
      {isDemoMode && (
        <div className="mb-6 px-4 py-3 rounded-lg border border-[var(--color-amber)]/40 bg-[var(--color-amber)]/5 text-sm text-[var(--color-amber)] flex items-center gap-2">
          <span className="font-semibold">Demo Mode</span>
          <span className="text-[var(--color-text-muted)]">—</span>
          <span className="text-[var(--color-text-muted)]">
            Serving fixture data. Set{" "}
            <code className="font-mono text-xs bg-[var(--color-border)] px-1.5 py-0.5 rounded">
              KRAKEN_DEMO_MODE=0
            </code>{" "}
            to connect to live Coral.
          </span>
        </div>
      )}

      {/* ── Page header ──────────────────────────────────────── */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Captain&apos;s Bridge
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          One SQL query over every system you run. Select a voyage and run it.
        </p>
      </header>

      {/* ── Summary strip ────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Voyages registered" value={voyageDefs.length.toString()} />
        <StatCard
          label="Sources covered"
          value={countUniqueSources(voyageDefs).toString()}
          accent="var(--color-teal)"
        />
        <StatCard
          label="Mode"
          value={isDemoMode ? "Demo" : "Live"}
          accent={isDemoMode ? "var(--color-amber)" : "var(--color-green)"}
        />
      </div>

      {/* ── Voyage grid ──────────────────────────────────────── */}
      {voyageDefs.length === 0 ? (
        <EmptyState />
      ) : (
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-4">
            Registered Voyages
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {voyageDefs.map((v) => (
              <VoyagePanel key={v.name} voyage={v} hero={v.name === "exec_escalation"} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function VoyagePanel({ voyage, hero }: { voyage: VoyageDef; hero?: boolean }) {
  return (
    <article
      className={`rounded-[var(--radius-card)] border bg-[var(--color-surface-raise)] p-5 flex flex-col gap-4
        ${hero ? "border-[var(--color-teal)]/50" : "border-[var(--color-border)]"}`}
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-[var(--color-text-primary)] text-sm font-mono">
              {voyage.name}
            </h3>
            {hero && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded border border-[var(--color-teal)]/40 text-[var(--color-teal)]">
                hero voyage
              </span>
            )}
          </div>
          {voyage.description && (
            <p className="text-xs text-[var(--color-text-muted)] mt-1 leading-relaxed">
              {voyage.description}
            </p>
          )}
        </div>
        {voyage.target_agent && (
          <span className="shrink-0 text-xs font-mono text-[var(--color-text-muted)] border border-[var(--color-border)] px-2 py-0.5 rounded">
            {voyage.target_agent}
          </span>
        )}
      </header>

      {/* Source list */}
      <div className="flex flex-wrap gap-1.5">
        {voyage.required_sources.map((s) => (
          <span
            key={s}
            className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-border)] text-[var(--color-text-muted)]"
          >
            {s}
          </span>
        ))}
      </div>

      {/* Launcher (client component) */}
      <VoyageLauncher voyage={voyage} />
    </article>
  );
}

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
        No voyages found. Check that the KRAKEN backend is running at{" "}
        <code className="font-mono bg-[var(--color-border)] px-1.5 py-0.5 rounded text-xs">
          localhost:8000
        </code>
        .
      </p>
    </div>
  );
}

function countUniqueSources(voyages: VoyageDef[]): number {
  const all = voyages.flatMap((v) => v.required_sources);
  return new Set(all).size;
}
