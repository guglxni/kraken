import type {
  ApiResponse,
  BenchResult,
  Finding,
  ReefGraph,
  TraceLineage,
  VoyageResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_KRAKEN_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    return {
      ok: false,
      data: null as unknown as T,
      error: `API error ${res.status}: ${res.statusText}`,
    };
  }

  const data = (await res.json()) as T;
  return { ok: true, data };
}

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: string;
  service: string;
  demo_mode: boolean;
}

export async function fetchHealth(): Promise<HealthStatus | null> {
  const result = await apiFetch<HealthStatus>("/api/health", { cache: "no-store" });
  return result.ok ? result.data : null;
}

// ─── Voyage definitions ───────────────────────────────────────────────────────

export interface VoyageDef {
  name: string;
  description?: string;
  required_sources: string[];
  target_agent?: string;
  params?: Record<string, unknown>[];
}

/** List all registered voyage definitions (no Coral required). */
export async function fetchVoyageDefs(): Promise<VoyageDef[]> {
  const result = await apiFetch<VoyageDef[]>("/api/voyages", {
    next: { revalidate: 60 },
  } as RequestInit);
  return result.ok ? result.data : [];
}

// ─── Run voyage (sync) ───────────────────────────────────────────────────────

export async function runVoyage(
  name: string,
  params: Record<string, unknown> = {}
): Promise<VoyageResult | null> {
  const result = await apiFetch<VoyageResult>("/api/voyages/run", {
    method: "POST",
    cache: "no-store",
    body: JSON.stringify({ voyage: name, params }),
  });
  return result.ok ? result.data : null;
}

// ─── SSE streaming ────────────────────────────────────────────────────────────

export type SseEvent =
  | { event: "start"; data: { voyage_id: string; voyage: string } }
  | { event: "compiled"; data: { sources: string[]; sql_length: number } }
  | { event: "executing"; data: { target_agent: string } }
  | {
      event: "finding";
      data: {
        finding_id: string;
        row_count: number;
        rows: Record<string, unknown>[];
        sources_queried?: string[];
        latency_ms?: number;
      };
    }
  | { event: "done"; data: { voyage_id: string; status: string } }
  | { event: "error"; data: { error: string } };

/**
 * Stream a voyage via SSE. Calls `onEvent` for each event.
 * Returns a cleanup function (abort the stream).
 */
export function streamVoyage(
  name: string,
  params: Record<string, unknown>,
  onEvent: (ev: SseEvent) => void
): () => void {
  const ctrl = new AbortController();

  (async () => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/voyages/stream`, {
        method: "POST",
        signal: ctrl.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voyage: name, params }),
      });
    } catch {
      onEvent({ event: "error", data: { error: "Connection failed" } });
      return;
    }

    if (!res.body) {
      onEvent({ event: "error", data: { error: "No response body" } });
      return;
    }

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += dec.decode(value, { stream: true });

      // SSE format: "event: X\ndata: Y\n\n"
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const lines = block.split("\n");
        let eventType = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7).trim();
          if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
        }
        if (eventType && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            onEvent({ event: eventType, data: parsed } as SseEvent);
          } catch {
            // malformed SSE block — skip
          }
        }
      }
    }
  })();

  return () => ctrl.abort();
}

// ─── Natural-language ask ─────────────────────────────────────────────────────

export async function askQuestion(
  question: string,
  params: Record<string, unknown> = {}
): Promise<VoyageResult | null> {
  const result = await apiFetch<VoyageResult>("/api/ask", {
    method: "POST",
    cache: "no-store",
    body: JSON.stringify({ question, params }),
  });
  return result.ok ? result.data : null;
}

// ─── Findings ────────────────────────────────────────────────────────────────

export async function fetchFindings(voyageId: string): Promise<Finding[]> {
  const result = await apiFetch<Finding[]>(`/api/findings?voyage_id=${voyageId}`, {
    next: { revalidate: 10 },
  } as RequestInit);
  return result.ok ? result.data : [];
}

// ─── Spyglass traces (backend-provided with column lineage) ────────────────────

import type { SpyglassTrace } from "./types";

/** Raw trace shape returned by GET /api/traces. */
interface RawTrace {
  trace_id: string;
  voyage_id: string;
  sql: string;
  plan?: string;
  sources: string[];
  duration_ms: number;
  row_count: number;
  created_at: string;
  lineage?: TraceLineage;
}

function mapTrace(t: RawTrace): SpyglassTrace {
  return {
    trace_id: t.trace_id,
    voyage_id: t.voyage_id,
    sql: t.sql,
    plan: t.plan ?? "",
    sources: t.sources ?? [],
    duration_ms: t.duration_ms,
    row_count: t.row_count,
    created_at: t.created_at,
    lineage: t.lineage,
  };
}

/** List recent SQL traces (now backend-provided with column lineage). */
export async function fetchTraces(limit = 20): Promise<SpyglassTrace[]> {
  const result = await apiFetch<RawTrace[]>(`/api/traces?limit=${limit}`, {
    next: { revalidate: 10 },
  } as RequestInit);

  if (!result.ok) return [];
  return result.data.map(mapTrace);
}

export async function fetchTrace(traceId: string): Promise<SpyglassTrace | null> {
  const result = await apiFetch<RawTrace>(`/api/traces/${traceId}`, {
    next: { revalidate: 10 },
  } as RequestInit);

  return result.ok ? mapTrace(result.data) : null;
}

// ─── Bench-O-Bot ───────────────────────────────────────────────────────────────

/** Fetch the Coral-vs-direct-MCP benchmark for a voyage. */
export async function fetchBench(voyage: string): Promise<BenchResult | null> {
  const result = await apiFetch<BenchResult>(`/api/bench?voyage=${encodeURIComponent(voyage)}`, {
    next: { revalidate: 30 },
  } as RequestInit);
  return result.ok ? result.data : null;
}

// ─── Reef Map ────────────────────────────────────────────────────────────────

export async function fetchReefGraph(voyageId: string): Promise<ReefGraph> {
  const result = await apiFetch<{
    nodes: { id: string; label: string; type: string }[];
    edges: { source: string; target: string; voyage_id: string }[];
  }>(`/api/reef-map/${voyageId}`, { next: { revalidate: 30 } } as RequestInit);

  if (!result.ok) return { nodes: [], links: [] };

  // Map API shape → ReefGraph shape
  return {
    nodes: result.data.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      source_kind: n.id as never,
      table_count: 3,
    })),
    links: result.data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      join_key: "id",
      voyage_id: e.voyage_id,
    })),
  };
}
