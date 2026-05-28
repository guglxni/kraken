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

export interface LineageNode {
  id: string;
  label: string;
  type: string;
}

export interface LineageEdge {
  source: string;
  target: string;
}

export interface LineageColumn {
  column: string;
  sources: string[];
}

export interface TraceLineage {
  tables: string[];
  columns: LineageColumn[];
  nodes: LineageNode[];
  edges: LineageEdge[];
  engine: string;
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
  lineage?: TraceLineage;
}

export interface BenchSide {
  approach: string;
  latency_ms: number;
  sources_queried: string[];
  row_count: number;
  token_count: number;
  tool_call_count: number;
  error: string | null;
}

export interface BenchResult {
  voyage_name: string;
  kraken: BenchSide;
  direct_mcp: BenchSide;
  latency_winner: string;
  coverage_winner: string;
  verdict: string;
  latency_speedup: number;
  direct_mcp_simulated: boolean;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  error?: string;
}
