import type { ApiResponse, Finding, ReefGraph, SpyglassTrace, VoyageResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_KRAKEN_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    // Next.js 15: opt in to cached fetch at the call site via `next.revalidate`
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

// ─── Voyages ─────────────────────────────────────────────────────────────────

/** Fetch the N most-recent voyage results. */
export async function fetchRecentVoyages(limit = 6): Promise<VoyageResult[]> {
  const result = await apiFetch<VoyageResult[]>(`/api/voyages?limit=${limit}`, {
    next: { revalidate: 30 },
  } as RequestInit);

  return result.ok ? result.data : [];
}

/** Fetch a single voyage result by ID. */
export async function fetchVoyage(voyageId: string): Promise<VoyageResult | null> {
  const result = await apiFetch<VoyageResult>(`/api/voyages/${voyageId}`, {
    next: { revalidate: 10 },
  } as RequestInit);

  return result.ok ? result.data : null;
}

// ─── Findings ────────────────────────────────────────────────────────────────

/** Fetch findings for a given voyage. */
export async function fetchFindings(voyageId: string): Promise<Finding[]> {
  const result = await apiFetch<Finding[]>(`/api/findings?voyage_id=${voyageId}`, {
    next: { revalidate: 10 },
  } as RequestInit);

  return result.ok ? result.data : [];
}

// ─── Reef Map ────────────────────────────────────────────────────────────────

/** Fetch the current Reef graph (nodes = sources, edges = JOIN relationships). */
export async function fetchReefGraph(): Promise<ReefGraph> {
  const result = await apiFetch<ReefGraph>("/api/reef", {
    next: { revalidate: 60 },
  } as RequestInit);

  return result.ok
    ? result.data
    : {
        nodes: [],
        links: [],
      };
}

// ─── Spyglass ────────────────────────────────────────────────────────────────

/** Fetch the most-recent SQL trace entries. */
export async function fetchTraces(limit = 20): Promise<SpyglassTrace[]> {
  const result = await apiFetch<SpyglassTrace[]>(`/api/traces?limit=${limit}`, {
    next: { revalidate: 10 },
  } as RequestInit);

  return result.ok ? result.data : [];
}

/** Fetch a single SQL trace by ID. */
export async function fetchTrace(traceId: string): Promise<SpyglassTrace | null> {
  const result = await apiFetch<SpyglassTrace>(`/api/traces/${traceId}`, {
    next: { revalidate: 5 },
  } as RequestInit);

  return result.ok ? result.data : null;
}
