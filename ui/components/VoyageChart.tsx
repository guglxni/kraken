"use client";

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  XAxis,
  YAxis,
} from "recharts";

// ─── Colour tokens ────────────────────────────────────────────────────────────

const TEAL = "hsl(174 62% 47%)";
const CORAL = "hsl(0 72% 65%)";
const AMBER = "hsl(38 92% 50%)";
const GREEN = "hsl(142 72% 45%)";

function severityColor(score: number): string {
  if (score >= 9) return "hsl(0 80% 55%)"; // critical — deep red
  if (score >= 7) return CORAL; // high — coral
  if (score >= 4) return AMBER; // medium — amber
  return GREEN; // low — green
}

function riskColor(score: number): string {
  if (score >= 80) return CORAL;
  if (score >= 60) return AMBER;
  return TEAL;
}

// ─── Hot Deploy — error rate before vs after ──────────────────────────────────

interface HotDeployRow {
  deploy_sha?: string;
  error_rate_before?: number;
  error_rate_after?: number;
  p99_latency_before_ms?: number;
  p99_latency_after_ms?: number;
  verdict?: string;
}

const hotDeployConfig: ChartConfig = {
  before: { label: "Before deploy", color: GREEN },
  after: { label: "After deploy", color: CORAL },
};

export function HotDeployChart({ rows }: { rows: HotDeployRow[] }) {
  const row = rows[0];
  if (!row) return null;

  const data = [
    {
      metric: "Error rate %",
      before: Number((row.error_rate_before ?? 0).toFixed(2)),
      after: Number((row.error_rate_after ?? 0).toFixed(2)),
    },
    {
      metric: "p99 latency (s)",
      before: Number(((row.p99_latency_before_ms ?? 0) / 1000).toFixed(2)),
      after: Number(((row.p99_latency_after_ms ?? 0) / 1000).toFixed(2)),
    },
  ];

  const isRollback = row.verdict === "ROLLBACK_RECOMMENDED";

  return (
    <div className="rounded-md border border-[var(--color-border)] p-4 bg-[var(--color-surface-raise)]">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-[var(--color-text-primary)]">Deploy Impact</h4>
        {isRollback && (
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full border border-[var(--color-coral)]/40 bg-[var(--color-coral)]/10 text-[var(--color-coral)]">
            ROLLBACK RECOMMENDED
          </span>
        )}
      </div>
      <ChartContainer config={hotDeployConfig} className="h-[180px]">
        <BarChart data={data} barGap={4}>
          <CartesianGrid vertical={false} stroke="var(--color-border)" strokeOpacity={0.5} />
          <XAxis
            dataKey="metric"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="before" fill={GREEN} radius={[3, 3, 0, 0]} />
          <Bar dataKey="after" fill={CORAL} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

// ─── Angry Whales — churn risk ranking ───────────────────────────────────────

interface AngryWhaleRow {
  customer?: string;
  company?: string;
  churn_risk_score?: number;
  mrr?: number;
}

const angryWhalesConfig: ChartConfig = {
  churn_risk_score: { label: "Churn risk score" },
};

export function AngryWhalesChart({ rows }: { rows: AngryWhaleRow[] }) {
  if (!rows.length) return null;

  const data = rows.slice(0, 8).map((r) => ({
    name: r.customer ?? r.company ?? "Unknown",
    churn_risk_score: Number((r.churn_risk_score ?? 0).toFixed(1)),
    mrr: r.mrr ?? 0,
  }));

  return (
    <div className="rounded-md border border-[var(--color-border)] p-4 bg-[var(--color-surface-raise)]">
      <h4 className="text-xs font-semibold text-[var(--color-text-primary)] mb-3">
        Churn Risk by Customer
      </h4>
      <ChartContainer config={angryWhalesConfig} className="h-[180px]">
        <BarChart data={data} layout="vertical" barSize={14} barGap={4}>
          <CartesianGrid horizontal={false} stroke="var(--color-border)" strokeOpacity={0.5} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
            width={90}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value, _name, props) => (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-[var(--color-text-muted)]">Risk score:</span>
                    <span className="font-mono font-semibold">{String(value)}</span>
                    <span className="text-[var(--color-text-muted)] ml-2">MRR:</span>
                    <span className="font-mono">
                      $
                      {Number(
                        (props.payload as Record<string, unknown>)?.mrr ?? 0
                      ).toLocaleString()}
                    </span>
                  </div>
                )}
              />
            }
          />
          <Bar dataKey="churn_risk_score" radius={[0, 3, 3, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={riskColor(entry.churn_risk_score)} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>
    </div>
  );
}

// ─── Exec Escalation — multi-system risk radar ───────────────────────────────

interface ExecEscalationRow {
  active_errors?: number;
  current_p99?: number;
  mrr?: number;
  open_incidents?: number;
  unpatched_cves?: number;
}

const execConfig: ChartConfig = {
  score: { label: "Risk score", color: CORAL },
};

export function ExecEscalationChart({ rows }: { rows: ExecEscalationRow[] }) {
  const row = rows[0];
  if (!row) return null;

  // Normalize each dimension to 0–100 for the radar
  const normalize = (val: number, max: number) => Math.min(100, Math.round((val / max) * 100));

  const data = [
    { axis: "Errors", score: normalize(row.active_errors ?? 0, 2000) },
    { axis: "Latency", score: normalize(row.current_p99 ?? 0, 8000) },
    { axis: "MRR risk", score: normalize(row.mrr ?? 0, 100000) },
    { axis: "Incidents", score: normalize(row.open_incidents ?? 0, 10) },
    { axis: "CVEs", score: normalize(row.unpatched_cves ?? 0, 20) },
  ];

  return (
    <div className="rounded-md border border-[var(--color-border)] p-4 bg-[var(--color-surface-raise)]">
      <h4 className="text-xs font-semibold text-[var(--color-text-primary)] mb-3">
        Risk Radar — Multi-System Overview
      </h4>
      <ChartContainer config={execConfig} className="h-[220px]">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="var(--color-border)" strokeOpacity={0.6} />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--color-text-muted)", fontSize: 10 }} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Radar
            dataKey="score"
            stroke={CORAL}
            fill={CORAL}
            fillOpacity={0.25}
            strokeWidth={2}
            dot={{ r: 3, fill: CORAL }}
          />
        </RadarChart>
      </ChartContainer>
    </div>
  );
}

// ─── Fresh CVE — severity bar chart ──────────────────────────────────────────

interface FreshCveRow {
  cve_id?: string;
  package_name?: string;
  severity_score?: number;
  severity?: string;
}

const cveConfig: ChartConfig = {
  severity_score: { label: "CVSS score" },
};

export function FreshCveChart({ rows }: { rows: FreshCveRow[] }) {
  if (!rows.length) return null;

  const data = rows.slice(0, 10).map((r) => ({
    name: r.cve_id ?? r.package_name ?? "Unknown",
    severity_score: Number((r.severity_score ?? 0).toFixed(1)),
  }));

  return (
    <div className="rounded-md border border-[var(--color-border)] p-4 bg-[var(--color-surface-raise)]">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-[var(--color-text-primary)]">
          CVE Severity (CVSS)
        </h4>
        <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <span
              className="inline-block w-2 h-2 rounded-sm"
              style={{ background: "hsl(0 80% 55%)" }}
            />
            Critical ≥9
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: CORAL }} />
            High ≥7
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: AMBER }} />
            Medium ≥4
          </span>
        </div>
      </div>
      <ChartContainer config={cveConfig} className="h-[180px]">
        <BarChart data={data} barSize={28}>
          <CartesianGrid vertical={false} stroke="var(--color-border)" strokeOpacity={0.5} />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 9 }}
          />
          <YAxis
            domain={[0, 10]}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="severity_score" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={severityColor(entry.severity_score)} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>
    </div>
  );
}

// ─── Dispatcher — picks the right chart for the voyage ───────────────────────

type AnyRow = Record<string, unknown>;

interface VoyageChartProps {
  voyageName: string;
  rows: AnyRow[];
}

export function VoyageChart({ voyageName, rows }: VoyageChartProps) {
  if (!rows.length) return null;

  switch (voyageName) {
    case "hot_deploy":
      return <HotDeployChart rows={rows as HotDeployRow[]} />;
    case "angry_whales":
      return <AngryWhalesChart rows={rows as AngryWhaleRow[]} />;
    case "exec_escalation":
      return <ExecEscalationChart rows={rows as ExecEscalationRow[]} />;
    case "fresh_cve":
      return <FreshCveChart rows={rows as FreshCveRow[]} />;
    default:
      return null;
  }
}
