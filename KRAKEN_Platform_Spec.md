# KRAKEN — Comprehensive Platform Specification
## Pirates of the Coral-bean | WeMakeDevs × Coral

> "One SQL query. Every system. Every voyage. The kraken sees what the org cannot."

---

## What KRAKEN Actually Is

KRAKEN is not a Coral app. KRAKEN is **the canonical developer surface for Coral** — a federated query platform, a visual voyage studio, a multi-agent swarm runtime, a source spec ecosystem, and a voyage library that any agent runtime can execute. It demonstrates every Coral primitive simultaneously, in a production-grade platform built on FOSS infrastructure.

**The architectural thesis:** Every existing enterprise tool in this space (Resolve.ai, Rootly, incident.io, FireHydrant, Aisera, Pylon, Snyk, Linear AI, Jira AI) is a chatbot over its own vertical silo. None of them can execute the JOIN that a VP-Eng's brain executes manually every morning. Coral's SQL-over-everything primitive is the first technology that makes that JOIN executable by an agent, locally, in one query plan, with caching, with no ETL. KRAKEN exposes that primitive as a complete developer platform — not a demo, not a dashboard, a platform.

---

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KRAKEN CAPTAIN'S BRIDGE (UI)                     │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │   Spyglass   │  │ Voyage Studio│  │  Reef Map  │  │Playground│  │
│  │  (chat/NL)   │  │ (JOIN editor)│  │ (causal    │  │(SQL REPL)│  │
│  │              │  │              │  │  graph)    │  │          │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  │
│         │                │                 │              │         │
│         └────────────────┴─────────────────┴──────────────┘         │
│                          AG-UI / CopilotKit                         │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│                      AGENT SWARM (CrewAI Flows)                     │
│                                                                     │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │Quartermaster│  │  Helm    │  │  Cooper  │  │      Purser      │ │
│  │  (planner)  │  │  (SRE)   │  │  (code)  │  │  (escalation)   │ │
│  └──────┬──────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│         │              │             │                  │           │
│         │         ┌────┴──┐    ┌─────┴──┐                           │
│         │         │ Bosun │    │Lookout │                           │
│         │         │(sprint)    │ (sec)  │                           │
│         │         └────┬──┘    └─────┬──┘                           │
│         │              │             │                              │
│         └──────────────┴─────────────┴── kraken.findings ───────┐  │
│                                          (Parquet blackboard)    │  │
└──────────────────────────────────────────────────┬───────────────┘  │
                                                   │                  │
┌──────────────────────────────────────────────────▼──────────────────┐
│                         CORAL (local)                               │
│              Single SQL runtime · MCP stdio · schema cache          │
│                                                                     │
│  ── bundled (21) ──────────────────────────────────────────────     │
│  github  sentry  slack  datadog  pagerduty  linear  confluence      │
│  intercom  grafana  statusgator  notion  stripe  jira  clickup      │
│  gitlab  launchdarkly  openobserve  posthog  cloudwatch  incident   │
│                                                                     │
│  ── custom specs (KRAKEN-built) ───────────────────────────────     │
│  osv  gmail  local-codebase  webhooks  kraken-graph                 │
│                                                                     │
│  ── local sources ─────────────────────────────────────────────     │
│  kraken.findings  kraken.plans  kraken.voyages  kraken.symbols      │
│  kraken.metrics   posthog.kraken  webhooks.deliveries               │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ OTLP
     ┌─────────────────────────────┼──────────────────────────────┐
     │                             │                              │
┌────▼──────┐  ┌──────────┐  ┌─────▼──────┐  ┌────────────────────┐
│ Langfuse  │  │ Supabase │  │ Trigger.dev│  │    PostHog (self)  │
│ (traces)  │  │(auth+db) │  │  (jobs)    │  │ (product analytics)│
└───────────┘  └──────────┘  └────────────┘  └────────────────────┘
```

---

## The Five Voyages (unified in one platform)

Every voyage is a parameterized SQL template in `kraken/voyages/*.yaml` plus a specialist agent that interprets results. Every voyage touches 4+ Coral sources. Every voyage exercises cross-source JOINs.

### Voyage 1: Hot Deploy (Coding Debugger)
**Question:** "What did we ship in the last 24h that is now on fire?"

**Sources:** `github.deployments × github.pulls × sentry.issues × datadog.metrics × slack.messages × local_codebase.symbols`

```sql
SELECT
  d.sha,
  p.title,
  p.user_login,
  p.additions,
  p.deletions,
  COUNT(s.id)                                               AS new_errors,
  AVG(m.latency_p99)
    - LAG(AVG(m.latency_p99)) OVER (ORDER BY d.created_at) AS p99_delta,
  array_agg(DISTINCT sym.name)                              AS touched_symbols,
  MAX(sm.ts)                                                AS last_oncall_message
FROM github.deployments d
JOIN github.pulls p
  ON p.merge_commit_sha = d.sha
JOIN sentry.issues s
  ON s.first_seen >= d.created_at
 AND s.environment = 'production'
JOIN datadog.metrics m
  ON m.timestamp BETWEEN d.created_at
                     AND d.created_at + INTERVAL '1 hour'
LEFT JOIN local_codebase.symbols sym
  ON sym.file = ANY(p.changed_files)
LEFT JOIN slack.messages sm
  ON sm.channel = '#oncall'
 AND sm.ts > d.created_at
WHERE d.created_at > NOW() - INTERVAL '24 hours'
GROUP BY d.sha, p.title, p.user_login, p.additions,
         p.deletions, d.created_at
HAVING COUNT(s.id) > 10
ORDER BY new_errors DESC;
```

### Voyage 2: Incident Auto-Summary (AI SRE)
**Question:** "Auto-summarize this PagerDuty incident with full context."

**Sources:** `pagerduty.incidents × github.deployments × github.pulls × datadog.metrics × statusgator.statuses × slack.messages × kraken.findings`

```sql
SELECT
  i.id,
  i.title,
  i.urgency,
  d.sha                                AS suspect_deploy,
  p.title                              AS suspect_pr,
  p.user_login                         AS author,
  sg.service                           AS third_party_outage,
  array_agg(DISTINCT sm.user)          AS responders,
  f.payload->>'resolution'             AS similar_past_resolution
FROM pagerduty.incidents i
LEFT JOIN github.deployments d
  ON d.created_at BETWEEN i.created_at - INTERVAL '30 min'
                      AND i.created_at
LEFT JOIN github.pulls p
  ON p.merge_commit_sha = d.sha
LEFT JOIN statusgator.statuses sg
  ON sg.status != 'up'
 AND sg.last_changed > i.created_at - INTERVAL '1 hour'
LEFT JOIN slack.messages sm
  ON sm.channel = '#inc-' || i.id
LEFT JOIN kraken.findings f
  ON f.kind = 'incident_resolution'
 AND f.payload->>'error_pattern' = i.title
WHERE i.status = 'triggered'
GROUP BY i.id, i.title, i.urgency, d.sha, p.title,
         p.user_login, sg.service, f.payload;
```

### Voyage 3: Stuck Sprint (Sprint Health)
**Question:** "Why is this sprint going to slip?"

**Sources:** `linear.issues × github.pulls × slack.messages × confluence.pages × jira.tickets × clickup.tasks`

```sql
SELECT
  l.identifier,
  l.title,
  l.assignee,
  l.state,
  NOW() - l.updated_at                         AS stuck_for,
  COUNT(DISTINCT pr.number)                    AS open_prs,
  COUNT(DISTINCT sm.id)                        AS slack_mentions_7d,
  cf.title                                     AS spec_doc,
  j.status                                     AS jira_mirror_status
FROM linear.issues l
LEFT JOIN github.pulls pr
  ON pr.body LIKE '%' || l.identifier || '%'
 AND pr.state = 'open'
LEFT JOIN slack.messages sm
  ON sm.text LIKE '%' || l.identifier || '%'
 AND sm.ts > NOW() - INTERVAL '7 days'
LEFT JOIN confluence.pages cf
  ON cf.body LIKE '%' || l.identifier || '%'
LEFT JOIN jira.tickets j
  ON j.external_id = l.identifier
WHERE l.state IN ('in_progress', 'in_review')
  AND l.updated_at < NOW() - INTERVAL '3 days'
ORDER BY stuck_for DESC;
```

### Voyage 4: Angry Whales (Customer Escalation)
**Question:** "Which open tickets are sitting on real production pain from high-MRR customers?"

**Sources:** `intercom.conversations × intercom.contacts × stripe.subscriptions × sentry.issues × grafana.dashboards × slack.messages × gmail.messages`

```sql
SELECT
  ic.id,
  ic.subject,
  c.email,
  sub.mrr,
  COUNT(DISTINCT s.id)              AS active_errors,
  g.dashboard_url,
  MAX(sm.ts)                        AS last_eng_response,
  gm.subject                        AS exec_email_subject
FROM intercom.conversations ic
JOIN intercom.contacts c
  ON c.id = ic.contact_id
JOIN stripe.subscriptions sub
  ON sub.customer_email = c.email
LEFT JOIN sentry.issues s
  ON s.tags->>'org' = sub.metadata->>'org_id'
 AND s.status = 'unresolved'
LEFT JOIN grafana.dashboards g
  ON g.tags @> ARRAY[sub.metadata->>'org_id']
LEFT JOIN slack.messages sm
  ON sm.text LIKE '%' || c.email || '%'
 AND sm.channel LIKE '#cs-%'
LEFT JOIN gmail.messages gm
  ON gm."from" = c.email
 AND gm.internal_date > NOW() - INTERVAL '24 hours'
WHERE ic.state = 'open'
  AND sub.mrr > 5000
GROUP BY ic.id, ic.subject, c.email, sub.mrr,
         g.dashboard_url, gm.subject
ORDER BY sub.mrr DESC, active_errors DESC;
```

### Voyage 5: Fresh CVE in Production (Security)
**Question:** "What new vulnerabilities landed in the last 24h that we are exposed to in production?"

**Sources:** `osv.vulnerabilities × osv.affected × github.dependencies × github.deployments × github.pulls × slack.messages × notion.pages`

```sql
SELECT
  v.id,
  v.summary,
  v.severity_score,
  d.sha                         AS deploy_id,
  d.created_at                  AS deployed_at,
  p.user_login                  AS author,
  n.title                       AS policy_doc
FROM osv.vulnerabilities v
JOIN osv.affected a
  ON a.vulnerability_id = v.id
JOIN github.dependencies dep
  ON dep.package_name = a.package_name
 AND dep.ecosystem    = a.ecosystem
JOIN github.deployments d
  ON d.repo = dep.repo
JOIN github.pulls p
  ON p.merge_commit_sha = d.sha
LEFT JOIN notion.pages n
  ON n.body LIKE '%' || a.package_name || '%'
 AND n.tags @> ARRAY['security-policy']
WHERE v.published > NOW() - INTERVAL '24 hours'
  AND v.severity_type = 'CVSS_V3'
  AND CAST(v.severity_score AS DOUBLE) >= 7.0
  AND d.environment = 'production'
ORDER BY v.severity_score DESC;
```

### Voyage 6: Executive Escalation (CEO email → full context)
**Sources:** `gmail.messages × intercom.contacts × stripe.subscriptions × sentry.issues × datadog.metrics × github.deployments × pagerduty.incidents × osv.vulnerabilities`

```sql
SELECT
  g.subject,
  g."from",
  g.snippet,
  c.name                                           AS customer,
  sub.mrr,
  COUNT(DISTINCT s.id)                             AS active_errors,
  MAX(m.latency_p99)                               AS current_p99,
  d.sha                                            AS last_deploy,
  d.created_at                                     AS deployed_at,
  COUNT(DISTINCT pd.id)                            AS open_incidents,
  COUNT(DISTINCT v.id)                             AS unpatched_cves
FROM gmail.messages g
JOIN intercom.contacts c
  ON c.email = g."from"
JOIN stripe.subscriptions sub
  ON sub.customer_email = c.email
LEFT JOIN sentry.issues s
  ON s.tags->>'org'    = sub.metadata->>'org_id'
 AND s.first_seen      > NOW() - INTERVAL '24 hours'
LEFT JOIN datadog.metrics m
  ON m.tags->>'org'    = sub.metadata->>'org_id'
 AND m.timestamp       > NOW() - INTERVAL '1 hour'
LEFT JOIN github.deployments d
  ON d.environment = 'production'
 AND d.created_at  = (
   SELECT MAX(d2.created_at)
   FROM github.deployments d2
   WHERE d2.environment = 'production'
 )
LEFT JOIN pagerduty.incidents pd
  ON pd.status = 'triggered'
LEFT JOIN osv.vulnerabilities v
  ON v.severity_score >= 7.0
 AND v.published       > NOW() - INTERVAL '7 days'
WHERE g.internal_date > NOW() - INTERVAL '6 hours'
  AND g.label_ids @> ARRAY['INBOX']
  AND sub.mrr > 10000
GROUP BY g.subject, g."from", g.snippet, c.name,
         sub.mrr, d.sha, d.created_at;
```

### Voyage 7: Risk Heatmap (morning briefing)
**Sources:** all 21 bundled + 2 custom simultaneously

```sql
WITH risks AS (
  SELECT 'deploy'   AS kind,
         sha        AS ref,
         COUNT(*)   AS weight
  FROM github.deployments
  WHERE created_at > NOW() - INTERVAL '24h'
  GROUP BY sha

  UNION ALL
  SELECT 'incident', id::text, urgency_score
  FROM pagerduty.incidents
  WHERE status = 'triggered'

  UNION ALL
  SELECT 'cve', id, severity_score
  FROM osv.vulnerabilities
  WHERE published > NOW() - INTERVAL '24h'
    AND severity_score >= 7.0

  UNION ALL
  SELECT 'whale', id::text, mrr
  FROM stripe.subscriptions
  WHERE status = 'past_due'
    AND mrr > 5000

  UNION ALL
  SELECT 'stale_pr', number::text, days_open
  FROM github.pulls
  WHERE state = 'open'
    AND created_at < NOW() - INTERVAL '7 days'

  UNION ALL
  SELECT 'sprint_slip', identifier, stuck_hours
  FROM linear.issues
  WHERE state IN ('in_progress', 'in_review')
    AND updated_at < NOW() - INTERVAL '3 days'
)
SELECT kind, ref, weight
FROM risks
ORDER BY weight DESC
LIMIT 50;
```

### Voyage 8: Stigmergic Self-Reference (architectural showpiece)
**Sources:** `kraken.findings × github.deployments × osv.vulnerabilities`

```sql
SELECT
  f.payload->>'cve_id'   AS cve,
  f.created_at           AS first_flagged,
  d.created_at           AS still_in_prod_at,
  v.severity_score       AS current_severity
FROM kraken.findings f
JOIN github.deployments d
  ON d.sha = f.payload->>'suspect_sha'
JOIN osv.vulnerabilities v
  ON v.id = f.payload->>'cve_id'
WHERE f.agent = 'lookout'
  AND f.kind  = 'cve_in_prod'
  AND d.environment = 'production'
  AND d.created_at  > f.created_at
ORDER BY v.severity_score DESC;
```

---

## Custom Coral Source Specs (5 — bounty eligible)

### 1. `osv` — OSV.dev vulnerability database
- **Auth:** none (public API)
- **Base URL:** `https://api.osv.dev/v1`
- **Tables:** `osv.vulnerabilities`, `osv.affected`, `osv.ranges`, `osv.references`, `osv.aliases`
- **Pagination:** cursor-based via `/v1/querybatch`
- **Bounty:** $100 + $50 charity
- **Upstream PR:** submit to `withcoral/coral`

### 2. `gmail` — Google Workspace Gmail
- **Auth:** OAuth2 CustomAuth (`gmail.readonly` scope)
- **Base URL:** `https://gmail.googleapis.com/gmail/v1/users/me`
- **Tables:** `gmail.messages`, `gmail.threads`, `gmail.labels`, `gmail.attachments`
- **Note:** Register Google Cloud OAuth client during the Foundation phase for verified status
- **Bounty:** $100 + $50 charity

### 3. `local-codebase` — local filesystem as SQL
- **Auth:** none (local)
- **Transport:** local-file Coral source extended with computed columns
- **Tables:** `local_codebase.files`, `local_codebase.symbols` (tree-sitter parse), `local_codebase.diffs` (git log)
- **Dependencies:** `tree-sitter` bindings, `libgit2`
- **Bounty:** $100 + $50 charity

### 4. `webhooks` — materialized webhook deliveries
- **Auth:** HMAC signature validation
- **Transport:** local HTTP receiver → JSONL append → Coral local-file
- **Tables:** `webhooks.deliveries`, `webhooks.subscriptions`
- **Value:** turns Coral into a real-time event source

### 5. `kraken-graph` — property graph via KuzuDB
- **Auth:** none (local)
- **Transport:** KuzuDB (embeddable, MIT) as storage backend
- **Tables:** `kraken_graph.entities`, `kraken_graph.relationships`, `kraken_graph.paths`
- **Value:** graph traversals JOINed with API data in one SQL plan

---

## Agent Swarm Design

### Agents (gitagent format, CrewAI runtime)

| Agent | Role | Reads | Writes |
|---|---|---|---|
| **Quartermaster** | Planner, router, synthesizer | `coral.tables`, `kraken.findings`, `kraken.plans` | `kraken.plans` |
| **Helm** | SRE Investigator | `pagerduty`, `datadog`, `statusgator`, `github.deployments`, `cloudwatch`, `openobserve` | `kraken.findings` |
| **Cooper** | Coding Debugger | `github`, `sentry`, `gitlab`, `launchdarkly`, `local_codebase`, `kraken.symbols` | `kraken.findings` |
| **Bosun** | Sprint Health | `linear`, `jira`, `clickup`, `github`, `slack`, `confluence`, `notion` | `kraken.findings` |
| **Purser** | Customer Escalation | `intercom`, `gmail`, `stripe`, `sentry`, `grafana`, `slack`, `posthog` | `kraken.findings` |
| **Lookout** | Security & Compliance | `osv`, `github`, `slack`, `notion`, `kraken_graph` | `kraken.findings` |

### Coordination Model
SQL-blackboard stigmergy. Agents never call each other directly.
- Quartermaster writes plans to `kraken.plans`
- Specialists poll `kraken.plans` for tasks tagged for them
- Specialists write findings to `kraken.findings` as Parquet rows
- Quartermaster JOINs `kraken.findings` to synthesize the final answer
- Any agent can JOIN `kraken.findings` with live sources (V8 pattern)

---

## Platform Features

### 1. Voyage Studio (Visual JOIN Editor)
**FOSS:** React Flow + monaco-editor + dnd-kit + sqlglot
- Drag sources from a palette onto a canvas
- Draw JOIN lines between columns; system infers key compatibility via Splink record-linkage
- Watch SQL compile in real-time in a monaco editor panel
- Schema for each source pulled live from `coral.tables` and `coral.columns`
- Export voyage as `voyage.yaml` in the voyage library
- Voyage linting via sqlglot AST analysis
- Voyage diff showing what changed between versions

### 2. Spyglass (Query Trace Inspector)
**FOSS:** Langfuse + OpenInference + uPlot + react-tanstack-table
- Every SQL query an agent issued: query text, source plan, row count, cache hit/miss, latency per source, token cost
- Coral execution plan visualization showing pushdown vs. post-process split
- Per-source latency waterfall using uPlot
- Bench-O-Bot: same query run via Coral vs. direct provider MCPs, side-by-side
- Export trace as OpenTelemetry OTLP for external ingestion

### 3. Reef Map (Live Causal Graph)
**FOSS:** React Flow + xyflow + d3-force + Mermaid
- Animates as agents write findings to `kraken.findings`
- Nodes: sources, entities (PRs, incidents, customers, CVEs)
- Edges: the JOIN relationships that connected them
- Click any node to drill into the raw Coral result
- Time-scrub: replay the graph building from t=0
- Export as Mermaid diagram (auto-posts to Confluence postmortem)
- Pre-computed layout for the hero demo flow (hand-tuned positions)

### 4. Coral Playground (SQL REPL)
**FOSS:** monaco-editor + @tanstack/react-table + mcp-client-sdk + sqlcoder (Ollama)
- monaco-editor with schema-aware autocomplete from `coral.tables` and `coral.columns`
- LSP backend in Python serving completion items from Coral schema discovery
- Run arbitrary Coral SQL against all connected sources
- Results in a sortable, filterable Tremor table
- NL-to-SQL via sqlcoder running locally on Ollama — type in English, get SQL
- Query history persisted in Supabase
- Share query via URL (query stored in Supabase, loaded via ID)
- Export results to CSV, Parquet, JSON

### 5. Voyage Library (dbt-for-Coral)
**FOSS:** Jinja2 + great-expectations + dbt-style YAML + Astro
- `kraken/voyages/*.yaml` — declarative voyage definitions
  ```yaml
  name: hot-deploy
  version: 1.0.0
  description: What shipped in 24h that is now on fire
  required_sources: [github, sentry, datadog, slack]
  parameters:
    - name: hours_back
      type: integer
      default: 24
  sql: hot_deploy.sql
  output_schema:
    - sha: string
    - new_errors: integer
    - p99_delta: float
  ```
- `voyage compile` — Jinja2 parameter injection into SQL templates
- `voyage test` — snapshot testing against fixture data
- `voyage lint` — sqlglot AST analysis, unused JOIN detection
- `voyage docs generate` — static Astro site with all voyages, sources, consumers
- `voyage marketplace` — community PR submissions with CI validation

### 6. Reef Memory (Query Learning Loop)
**FOSS:** LanceDB + fastembed + sqlite-vec
- Every successful voyage SQL + outcome embedded via fastembed (local, no API call)
- Stored in LanceDB (embedded, Rust, MIT)
- Before each new voyage, vector search retrieves top-3 most similar prior voyages
- Injected as few-shot exemplars into the Quartermaster's system prompt
- Second run of same incident class: provably faster, cheaper, more accurate
- Reef Memory dashboard in Tremor showing hit rate over time

### 7. Source Spec Forge
**FOSS:** openapi-typescript-codegen + graphql-codegen + ajv + semgrep
- **OpenAPI → Coral spec:** paste an OpenAPI 3.1 spec, get a Coral YAML source spec
- **GraphQL → Coral spec:** paste a schema, get a Coral YAML source spec
- **Visual form:** paste a curl command (via curlconverter), generate YAML
- **Spec linter:** ajv schema validation + semgrep pattern rules
- **Spec test harness:** VCR.py-style HTTP fixture recording, replay in CI
- **Spec hot-reload:** watchdog watches spec file, replays last query on change
- **Spec marketplace:** `coral source install github.com/org/spec` with sigstore verification

### 8. Schema Intelligence Layer
**FOSS:** Splink + DataSketches + Presidio + detect-secrets
- **Inferred foreign key detection:** Splink record-linkage across all sources, proposes JOIN keys
- **PII classification:** Presidio NER-based detection on all Coral source columns
- **Secret detection:** detect-secrets scans query results for credential patterns
- **Schema diff:** compare today's schema vs. last week's, surface breaking changes
- **Schema-aware autocomplete:** available everywhere SQL is written in KRAKEN

### 9. Bench-O-Bot (Live Benchmark Harness)
**FOSS:** Langfuse + OpenTelemetry + uPlot
- Runs identical voyage twice: once via Coral MCP, once via direct provider MCPs
- Measures: latency, token count, cost, accuracy score (LLM-as-judge via promptfoo)
- Renders side-by-side in Spyglass
- Reference frame: Coral's published 31% / 3.4× / 42% numbers
- Framing: "Coral's published benchmarks; our workload measured X/Y/Z"
- Records results to Supabase for trend tracking over time

### 10. Notification and Action Layer
**FOSS:** Knock/Novu + Resend + Composio MCP + Trigger.dev
- **Read-side:** Coral SQL (only data path for reads)
- **Write-side:** Composio MCP tools for write actions
  - Create Linear ticket
  - Post Slack message
  - Draft GitHub PR
  - Write Confluence page
  - Send email via Resend (live during demo — judge sees email arrive)
  - Page via PagerDuty
- **Notification routing:** Knock for multi-channel alerts (Slack/email/SMS/in-app)
- **Scheduled voyages:** Trigger.dev for cron + event-driven execution with retries

### 11. Auth and Multi-Tenancy
**FOSS:** Supabase Auth + Better Auth + Postgres RLS
- Supabase Auth handles OAuth for all providers (Google, GitHub, Slack, Linear, Notion)
- Coral source specs read tokens from Supabase credential store (not local trust store)
- Postgres RLS scopes all `kraken.findings`, `kraken.plans`, voyage history per org
- Demo moment: two browser tabs, two orgs, same KRAKEN deployment, isolated data
- Better Auth for organization-based multi-tenancy layer on top

### 12. Observability Stack
**FOSS:** Langfuse + OpenInference + OpenTelemetry + PostHog
- **Langfuse** (self-hosted): all LLM traces, prompt management, cost tracking
- **OpenInference**: OpenTelemetry spans for every agent action, every Coral SQL
- **OTLP**: single trace ID across Rust (Coral) + Python (agents) + TS (UI)
- **PostHog** (self-hosted): product analytics on KRAKEN's own usage
  - Which voyages run most
  - Which sources queried most
  - Which agents fail most
  - Session replay for UX improvement
- **Meta-moment:** PostHog is a Coral bundled source, so KRAKEN can query its own analytics via `coral sql "SELECT * FROM posthog.events WHERE event = 'voyage_run'"` — self-referential closure

### 13. Data Quality and Governance
**FOSS:** great-expectations + OpenLineage + Marquez + datacontract-cli
- **great-expectations:** voyage output assertions (non-null, value ranges, row counts)
- **OpenLineage:** every voyage emits lineage events to Marquez
- **Data contracts:** each voyage publishes a typed output contract via datacontract-cli
- **Audit log:** append-only log of every agent action in Supabase
- **Column-level lineage:** which result row came from which source row

### 14. Developer Experience Layer
**FOSS:** Click + prompt_toolkit + watchdog + py-spy
- **`kraken` CLI:** full voyage execution from terminal
  - `kraken voyage:run hot-deploy --since=24h`
  - `kraken voyage:compile`
  - `kraken voyage:test`
  - `kraken voyage:lint`
  - `kraken voyage:docs`
  - `kraken source:forge --openapi ./spec.yaml`
  - `kraken bench --voyage hot-deploy`
- **Voyage REPL:** interactive shell with autocomplete via prompt_toolkit
- **Hot reload:** watchdog watches agent SOUL.md files, reloads without restart
- **Voyage profiler:** py-spy flamegraph of voyage execution time
- **One-command bootstrap:** `npx create-kraken-voyage` scaffolds a new voyage

### 15. Public API and SDK
**FOSS:** FastAPI + strawberry-graphql + openapi-generator
- REST API: `POST /api/voyages/{name}/run`
- GraphQL API via strawberry-graphql
- Auto-generated OpenAPI spec
- Client SDKs in Python, TypeScript, Go via openapi-generator
- Embeddable web component: `<kraken-voyage name="hot-deploy">` via Lit
- Webhook output: voyage results can fire to any webhook

---

## Production Infrastructure

### Supabase (Platform Spine)
- **Auth:** Google/GitHub/Slack OAuth — no "unverified app" screens
- **Postgres:** DBOS durable execution state, voyage history, credential store
- **RLS:** per-org isolation on all tables
- **Realtime:** Reef Map streams updates as agents append to `kraken.findings`
- **Storage:** Parquet ship's log files, S3-compatible, versioned

### DBOS Transact (Durable Execution)
- Every voyage is a DBOS workflow
- Steps: each agent invocation, each Coral SQL, each write action
- Demo moment: kill the process mid-voyage, restart, it resumes from last checkpoint
- Replay any past voyage from any step via DBOS time-travel

### Trigger.dev (Scheduled Jobs)
- Morning briefing: 08:30 cron, runs Voyage 7 (Risk Heatmap), posts to Slack
- Event-driven triggers: deploy event → auto-run Voyage 1 (Hot Deploy)
- Retry semantics on all scheduled voyages

---

## FOSS Stack Reference

### Core
| Component | Library | License |
|---|---|---|
| Federated query | Coral (withcoral/coral) | Apache 2.0 |
| Agent orchestration | CrewAI + Flows | MIT |
| Durable execution | DBOS Transact | MIT |
| Typed handoffs | PydanticAI | MIT |
| LLM gateway | LiteLLM | MIT |
| Model | Claude Opus 4.6 | Anthropic API |

### Data
| Component | Library | License |
|---|---|---|
| Analytical store | DuckDB | MIT |
| Vector search | LanceDB | Apache 2.0 |
| Graph database | KuzuDB | MIT |
| Embeddings | fastembed | Apache 2.0 |
| Record linkage | Splink | MIT |
| Data quality | great-expectations | Apache 2.0 |
| Data lineage | OpenLineage + Marquez | Apache 2.0 |
| Data contracts | datacontract-cli | MIT |

### Observability
| Component | Library | License |
|---|---|---|
| LLM observability | Langfuse (self-hosted) | MIT |
| OTel instrumentation | OpenInference | Apache 2.0 |
| Product analytics | PostHog (self-hosted) | MIT |
| LLM eval | promptfoo | MIT |
| SQL profiling | py-spy | MIT |

### Frontend
| Component | Library | License |
|---|---|---|
| Framework | Next.js 16 + React 19 | MIT |
| Agent-UI protocol | CopilotKit + AG-UI | MIT |
| Chat shell | assistant-ui | MIT |
| Graph visualization | React Flow / xyflow | MIT |
| Dashboard components | Tremor | Apache 2.0 |
| UI chrome | shadcn/ui | MIT |
| SQL editor | monaco-editor | MIT |
| Time-series charts | uPlot | MIT |
| Data table | @tanstack/react-table | MIT |
| Real-time collab | Yjs | MIT |

### Source Spec Tooling
| Component | Library | License |
|---|---|---|
| SQL parsing | sqlglot | MIT |
| Static analysis | semgrep | LGPL 2.1 |
| Schema validation | ajv | MIT |
| OpenAPI codegen | openapi-typescript-codegen | MIT |
| GraphQL codegen | graphql-codegen | MIT |
| curl parsing | curlconverter | MIT |
| HTTP fixtures | VCR.py | MIT |
| File watching | watchdog | Apache 2.0 |

### Code Understanding
| Component | Library | License |
|---|---|---|
| AST parsing | tree-sitter bindings | MIT |
| Repo map | Aider repomap.py (ported) | Apache 2.0 |
| Pattern matching | ast-grep | MIT |

### Infrastructure
| Component | Library | License |
|---|---|---|
| Auth + DB + Storage | Supabase | Apache 2.0 |
| Auth layer | Better Auth | MIT |
| Job scheduling | Trigger.dev | Apache 2.0 |
| Notification routing | Knock / Novu | MIT |
| Email sending | Resend | MIT |
| Write-side actions | Composio MCP | MIT |
| Secrets management | Infisical | MIT |
| Local NL-to-SQL | sqlcoder via Ollama | Apache 2.0 |
| Static docs site | Astro | MIT |
| Web component | Lit | BSD-3 |

### Security
| Component | Library | License |
|---|---|---|
| PII detection | Presidio | MIT |
| Secret detection | detect-secrets | Apache 2.0 |
| Policy enforcement | OPA | Apache 2.0 |
| Hallucination detection | selfcheckgpt | MIT |

---

## Hackathon Bounties Targeted

| Bounty | How KRAKEN wins it |
|---|---|
| **Track 1 Winner** (MacBook Neo × 4) | Strongest cross-source JOIN demonstration, category-of-one positioning, all five voyages unified |
| **Custom Source: `osv`** ($100 + $50 charity) | Fully implemented, upstream PR submitted |
| **Custom Source: `gmail`** ($100 + $50 charity) | Fully implemented, upstream PR submitted |
| **Custom Source: `local-codebase`** ($100 + $50 charity) | Implemented, upstream PR submitted |
| **Discord Showcase** (Claude Max vouchers) | Post in #how-i-coral with screenshots + writeup |
| **Best Guide** (Keychron keyboard) | 2-3 page reproducible blog post submitted with hackathon entry |
| **Early Bird Swag** | Register + post on LinkedIn/X early in the hackathon window |

---

## Demo Script

**Segment 1 — Cold open.**
"Every morning, the VP of Engineering opens five tabs, asks five questions, and stitches the answers in their head. We replaced that with one query."

**Segment 2 — The setup.**
Terminal: `coral source list` → 23 sources connected (21 bundled + osv + gmail). Cut to KRAKEN UI: Spyglass on left, blank Reef Map on right.

**Segment 3 — The hostile email arrives.**
Gmail notification: "URGENT — Acme is churning. Dashboard down three hours. Status page lies." User types: "Why is Acme churning right now?" Reef Map begins animating — tentacle edges draw from gmail.messages → intercom.contacts → stripe.subscriptions ($240K ARR) → sentry.issues (3,400 errors) → datadog.metrics (p99 12s) → github.deployments → github.pulls → osv.vulnerabilities (critical CVE).

**Segment 4 — Spyglass shows the receipts.**
Switch to Spyglass. One SQL plan. 12 sources. 14 seconds wall-clock. $0.04 token cost. Bench-O-Bot fires: same question via direct MCPs → 38 tool calls, 47 seconds, $0.14.

**Segment 5 — The voyage library.**
Quick cut to Voyage Studio — the visual JOIN editor building the same query graphically. Cut to `kraken/voyages/` directory — 8 YAML voyage definitions. Cut to auto-generated docs site.

**Segment 6 — The five voyages.**
Quick cuts: sprint-blockers Reef Map, CVE-in-prod with OSV source spec visible, DBOS crash-and-resume demo (kill process mid-voyage, it picks back up), morning briefing Slack post.

**Segment 7 — Self-referential closure.**
`coral sql "SELECT * FROM posthog.events WHERE event = 'voyage_run'"` — KRAKEN querying its own usage through Coral.

**Segment 8 — Close.**
"KRAKEN is not a Coral demo. KRAKEN is the canonical developer surface for Coral. A visual query builder, a voyage library, a multi-agent swarm, a source spec forge, and the infrastructure for the next generation of agent data platforms. Single binary. Local-first. Apache 2.0."

---

## Win Probability by Judging Criterion

| Criterion | Signal | Confidence |
|---|---|---|
| **Potential Impact** | VP-Eng and Platform-team pain across 50-500 eng SaaS companies, backed by named competitors missing the JOIN primitive | High |
| **Creativity & Originality** | SQL-blackboard stigmergy; Voyage Studio as first visual Coral IDE; self-referential PostHog query; Source Spec Forge turning any OpenAPI into a Coral source | High |
| **Learning & Growth** | Rust source specs, CrewAI Flows, gitagent format, OpenLineage, Better Auth, data contracts — documented in README's learning log | High |
| **Technical Implementation** | 23 Coral sources, 8 voyage queries all cross-source, MCP + CLI both demonstrated, DBOS durable execution, full OTel tracing, 5 custom specs | High |
| **Aesthetics & UX** | Reef Map animated causal graph, Voyage Studio visual editor, Spyglass query inspector, Tremor dashboard, maritime theme restrained but consistent | High |
| **Best Use of Coral** | Coral is literally the only data path. Every feature exercises a different Coral primitive. Bench-O-Bot makes the advantage measurable on stage. Schema discovery powers the IDE. Local-file sources enable the blackboard. Custom specs extend the ecosystem. | Ceiling |

---

## Positioning Statement (README opening paragraph)

> KRAKEN is the canonical developer surface for Coral — a federated query platform that gives engineering organizations a single SQL interface over every system they run. It ships a visual voyage studio, a live causal graph, a query playground, a source spec forge, a canonical voyage library, and a multi-agent swarm that orchestrates everything. Every read goes through Coral SQL. Every write goes through typed MCP actions. The platform is local-first, Apache 2.0, and built to demonstrate what becomes possible when you treat SQL-over-APIs as the foundation for the next generation of agent infrastructure.
