export interface Finding {
  finding_id: string;
  voyage_id: string;
  agent: string;
  kind: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface VoyageResult {
  voyage_id: string;
  name: string;
  status: "pending" | "running" | "done" | "failed";
  rows: Record<string, unknown>[];
  row_count: number;
  latency_ms: number;
  sources_queried: string[];
  created_at: string;
}

export interface CoralSource {
  id: string;
  name: string;
  kind: "github" | "sentry" | "stripe" | "linear" | "datadog" | "osv" | "gmail" | "slack";
  schema_tables: string[];
  last_queried_at: string | null;
}

export interface ReefNode {
  id: string;
  label: string;
  source_kind: CoralSource["kind"];
  table_count: number;
}

export interface ReefEdge {
  source: string;
  target: string;
  join_key: string;
  voyage_id: string;
}

export interface ReefGraph {
  nodes: ReefNode[];
  links: ReefEdge[];
}

export interface SpyglassTrace {
  trace_id: string;
  voyage_id: string;
  sql: string;
  plan: string;
  sources: string[];
  duration_ms: number;
  row_count: number;
  created_at: string;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  error?: string;
}
