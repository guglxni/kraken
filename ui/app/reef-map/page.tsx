import { ReefMap } from "@/components/ReefMap";
import { fetchReefGraph } from "@/lib/api";

export const dynamic = "force-dynamic";

// Hero demo voyage ID — used when no voyage_id is specified
const DEMO_VOYAGE_ID = "demo-v6-acme-001";

interface ReefMapPageProps {
  searchParams: Promise<{ voyage_id?: string }>;
}

export default async function ReefMapPage({ searchParams }: ReefMapPageProps) {
  const { voyage_id } = await searchParams;
  const vid = voyage_id ?? DEMO_VOYAGE_ID;
  const graph = await fetchReefGraph(vid);

  const nodeCount = graph.nodes.length;
  const edgeCount = graph.links.length;

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="shrink-0 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Reef Map</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            Causal graph of Coral source relationships from voyage{" "}
            <code className="font-mono text-xs bg-[var(--color-border)] px-1 rounded">{vid}</code>.
          </p>
        </div>

        <div className="flex items-center gap-6 text-xs text-[var(--color-text-muted)]">
          <span>
            <span className="font-mono text-[var(--color-text-primary)] font-semibold mr-1">
              {nodeCount}
            </span>
            sources
          </span>
          <span>
            <span className="font-mono text-[var(--color-text-primary)] font-semibold mr-1">
              {edgeCount}
            </span>
            JOIN relationships
          </span>
        </div>
      </header>

      {/* ── Legend ─────────────────────────────────────────── */}
      <div className="shrink-0 flex flex-wrap gap-3">
        {LEGEND_ITEMS.map((item) => (
          <div
            key={item.kind}
            className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]"
          >
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            {item.kind}
          </div>
        ))}
      </div>

      {/* ── Graph canvas ───────────────────────────────────── */}
      <div className="flex-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] overflow-hidden min-h-0">
        <ReefMap graph={graph} />
      </div>
    </div>
  );
}

const LEGEND_ITEMS = [
  { kind: "github", color: "#6e8efb" },
  { kind: "sentry", color: "#f76b8a" },
  { kind: "stripe", color: "#6f72e2" },
  { kind: "linear", color: "#4e8ce4" },
  { kind: "datadog", color: "#b57bee" },
  { kind: "osv", color: "#ff6b6b" },
  { kind: "gmail", color: "#e06c75" },
  { kind: "slack", color: "#56b6c2" },
] as const;
