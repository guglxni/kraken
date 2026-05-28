"use client";

import { useState } from "react";
import { type Field, QueryBuilder, type RuleGroupType, formatQuery } from "react-querybuilder";
import "react-querybuilder/dist/query-builder.css";

/**
 * Voyage Studio — visual WHERE-clause composer.
 *
 * Client Component. Lets you visually compose filter predicates over common
 * voyage parameters and emits the generated Coral SQL WHERE clause via
 * `formatQuery(query, "sql")`. Self-contained — no backend call required; the
 * generated clause is meant to be merged into a voyage YAML template.
 */

// ── Voyage parameter fields available to filter on ──────────────────────────────
const FIELDS: Field[] = [
  { name: "hours_back", label: "hours_back", inputType: "number" },
  { name: "severity", label: "severity (CVSS)", inputType: "number" },
  { name: "churn_risk_score", label: "churn_risk_score", inputType: "number" },
  { name: "mrr", label: "mrr ($)", inputType: "number" },
  { name: "error_rate", label: "error_rate (%)", inputType: "number" },
  { name: "p99_latency_ms", label: "p99_latency_ms", inputType: "number" },
  { name: "open_incidents", label: "open_incidents", inputType: "number" },
  { name: "unpatched_cves", label: "unpatched_cves", inputType: "number" },
  {
    name: "source",
    label: "source",
    valueEditorType: "select",
    values: [
      { name: "github", label: "github" },
      { name: "sentry", label: "sentry" },
      { name: "stripe", label: "stripe" },
      { name: "linear", label: "linear" },
      { name: "datadog", label: "datadog" },
      { name: "osv", label: "osv" },
      { name: "gmail", label: "gmail" },
      { name: "slack", label: "slack" },
    ],
  },
];

const INITIAL_QUERY: RuleGroupType = {
  combinator: "and",
  rules: [
    { field: "hours_back", operator: "<=", value: "24" },
    { field: "severity", operator: ">=", value: "7.0" },
  ],
};

export default function VoyageStudioPage() {
  const [query, setQuery] = useState<RuleGroupType>(INITIAL_QUERY);

  const whereClause = formatQuery(query, "sql");

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Voyage Studio</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Visual WHERE-clause composer — build multi-source voyage filters without writing raw SQL
          predicates.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Builder ──────────────────────────────────────────── */}
        <section className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-4">
            Filter Conditions
          </h2>
          <div className="kraken-querybuilder">
            <QueryBuilder
              fields={FIELDS}
              query={query}
              onQueryChange={setQuery}
              controlClassnames={{
                queryBuilder: "text-xs",
              }}
            />
          </div>
        </section>

        {/* ── Generated SQL ────────────────────────────────────── */}
        <section className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] p-5 flex flex-col gap-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
              Generated WHERE Clause
            </h2>
            <pre className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-xs font-mono text-[var(--color-text-primary)] overflow-x-auto leading-relaxed whitespace-pre-wrap">
              {whereClause || "-- add a condition to generate SQL"}
            </pre>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-2">
              Merge this clause into a voyage template in{" "}
              <code className="font-mono bg-[var(--color-border)] px-1 py-0.5 rounded">
                kraken/voyages/
              </code>
              .
            </p>
          </div>

          <div>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
              Serialised Rules (JSON)
            </h2>
            <pre className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-xs font-mono text-[var(--color-text-muted)] overflow-x-auto leading-relaxed whitespace-pre-wrap">
              {formatQuery(query, "json_without_ids")}
            </pre>
          </div>
        </section>
      </div>
    </div>
  );
}
