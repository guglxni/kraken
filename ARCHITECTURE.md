# ARCHITECTURE.md — KRAKEN System Design

> Read this after CLAUDE.md. This document defines the structural decisions that the coding agent must respect.

---

## Architectural thesis

Every existing tool in the enterprise observability / incident / customer-escalation / security space is a chatbot bolted onto its own vertical data silo. None of them can execute the JOIN that a VP-Engineering's brain executes manually every morning. Coral's federated SQL primitive is the first technology that makes that JOIN executable by an agent, locally, in one query plan, with caching, with no ETL, and with no data leaving the laptop. KRAKEN is the platform that exposes that primitive as a complete developer surface.

---

## Layer model

The system is layered. Each layer has strict boundaries.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 6: Presentation                                          │
│  Next.js 16 + React 19 + CopilotKit + shadcn/ui + Tremor        │
│  Voyage Studio · Spyglass · Reef Map · Playground · Captain's   │
│  Bridge                                                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ AG-UI protocol (SSE + WebSocket)
┌──────────────────────────────▼──────────────────────────────────┐
│  Layer 5: Agent Orchestration                                   │
│  CrewAI Flows + PydanticAI + DBOS                                │
│  Quartermaster (planner) routes to specialists; specialists     │
│  coordinate via SQL blackboard                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ MCP stdio
┌──────────────────────────────▼──────────────────────────────────┐
│  Layer 4: Federated Query                                       │
│  Coral (Apache 2.0, Rust)                                       │
│  Single SQL plan over 23 sources; schema cache; query           │
│  pushdown; result caching                                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (per-source) + local files
┌──────────────────────────────▼──────────────────────────────────┐
│  Layer 3: Source Specs                                          │
│  21 bundled (github, sentry, slack, datadog, etc.) +            │
│  5 custom (osv, gmail, local-codebase, webhooks, kraken-graph)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Layer 2: External APIs + Local Storage                         │
│  GitHub API, Sentry API, Slack API, ... + Parquet ship's log    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Infrastructure (orthogonal to all above)              │
│  Supabase (auth + Postgres + Realtime + Storage) ·              │
│  Trigger.dev (scheduled jobs) · Langfuse (LLM traces) ·         │
│  PostHog (product analytics) · DBOS (durable execution)         │
└─────────────────────────────────────────────────────────────────┘
```

### Layer rules

- **Layer 6 (UI)** talks only to Layer 5 via AG-UI. It never imports Coral clients directly.
- **Layer 5 (Agents)** talks only to Layer 4 via MCP. It never imports source API clients.
- **Layer 4 (Coral)** is a black box to higher layers. Its internal architecture is owned by withcoral/coral.
- **Layer 3 (Source Specs)** is declarative YAML. No Python or TypeScript belongs here.
- **Layer 1 (Infra)** is accessed via well-defined SDK boundaries. Never reach into Postgres directly when Supabase's client suffices.

---

## Component catalog

### Coral Client (`kraken/coral_client.py`)
Thin wrapper around the MCP stdio transport to Coral. Exposes `coral_sql(query: str) → ResultSet`. Single entry point for all data access. Wraps every call in OpenTelemetry spans with `coral.sql.text`, `coral.sql.sources`, `coral.sql.row_count`, `coral.sql.latency_ms`, `coral.sql.cache_hit` attributes.

### Crew (`kraken/crew.py`)
CrewAI Flows orchestration. Defines:
- Six agents loaded from `agents/*/`
- Two flows: `interactive_voyage` (user-driven) and `scheduled_voyage` (cron/event-driven)
- Routing logic: Quartermaster classifies the request, dispatches to one or more specialists

### Blackboard (`kraken/blackboard.py`)
Manages the Parquet ship's log at `~/.kraken/findings.parquet`. Exposes:
- `write_finding(agent: str, kind: str, payload: dict) → finding_id`
- `read_findings(filter: dict) → list[Finding]`
- Registered with Coral as the `kraken.findings` local-file source on startup.

### Reef Memory (`kraken/reef_memory.py`)
LanceDB-backed vector index over past successful voyages. Exposes:
- `record_voyage(voyage_id: str, sql: str, outcome: str, score: float)`
- `recall_similar(query: str, top_k: int = 3) → list[Voyage]`
- Used by Quartermaster to inject few-shot exemplars into specialist prompts.

### Bench-O-Bot (`kraken/bench.py`)
Comparison harness. Runs the same query twice:
1. Via Coral MCP
2. Via direct provider MCPs (GitHub MCP, Sentry MCP, etc.)
Measures latency, token count, cost, accuracy (LLM-as-judge via promptfoo). Renders side-by-side in Spyglass.

### Voyage Compiler (`kraken/voyages/compiler.py`)
Reads voyage YAML, compiles Jinja2 SQL templates with parameters, validates output schema against declared contract. Exposes `compile_voyage(name: str, params: dict) → CompiledVoyage`.

### CLI (`kraken/cli.py`)
Click-based command-line interface. Subcommands:
- `kraken voyage:run NAME [--param key=val]`
- `kraken voyage:compile NAME`
- `kraken voyage:test`
- `kraken voyage:lint`
- `kraken voyage:docs`
- `kraken source:forge --openapi PATH`
- `kraken source:lint NAME`
- `kraken source:test NAME`
- `kraken bench --voyage NAME`

---

## Data flow: the hero voyage

This is the demo path. Trace this end-to-end before modifying any component.

```
1. User opens Spyglass and types:
   "Why is Acme churning right now?"
        │
        ▼
2. UI sends via AG-UI to the agent runtime.
        │
        ▼
3. Quartermaster receives the question.
   - Calls reef_memory.recall_similar("acme churn") → top 3 past voyages
   - Injects those as few-shot exemplars
   - Decides this is an executive-escalation voyage
   - Writes plan to kraken.plans:
     {kind: "exec_escalation", target: "purser", priority: "high"}
        │
        ▼
4. Purser polls kraken.plans, picks up the plan.
   - Reads voyages/exec_escalation.yaml
   - Compiles SQL with params {sender: "acme.ceo@..."}
   - Issues single coral_sql() call
        │
        ▼
5. Coral executes the cross-source JOIN:
   gmail.messages × intercom.contacts × stripe.subscriptions
   × sentry.issues × datadog.metrics × github.deployments
   × github.pulls × pagerduty.incidents × osv.vulnerabilities
        │
        ▼
6. Coral pushes filters to each source API in parallel,
   merges results in one query plan, returns ResultSet.
        │
        ▼
7. Purser writes finding to kraken.findings:
   {agent: "purser", kind: "exec_escalation_brief",
    payload: {customer, mrr, root_cause, suggested_actions}}
        │
        ▼
8. Quartermaster sees the finding (via realtime subscription).
   - JOINs the finding with live state (V8 stigmergic pattern)
   - Synthesizes a 4-bullet plain-English summary
   - Drafts write-side actions via Composio MCP:
     a. CEO reply email (Resend)
     b. PagerDuty page
     c. Rollback PR draft (GitHub)
     d. Linear ticket (onboarding gap)
        │
        ▼
9. UI streams the synthesis via AG-UI.
   - Reef Map animates: edges draw between every JOIN'd entity
   - Spyglass shows the SQL plan with per-source latency
   - Bench-O-Bot renders Coral-vs-direct-MCP comparison
   - Captain's Bridge offers Anchor approval on each write action
```

---

## State management

### Durable state (Supabase Postgres + DBOS)
- Voyage execution history (idempotency)
- Agent run logs (replay)
- User auth and credential refresh tokens
- Voyage definitions (synced from `kraken/voyages/`)
- Audit log (immutable, append-only)

### Ephemeral state (DuckDB + LanceDB local)
- Coral query result cache (in-memory)
- LanceDB vector index for Reef Memory
- DuckDB analytical workspace

### Blackboard state (Parquet)
- `kraken.findings` — agent-written discoveries
- `kraken.plans` — Quartermaster-issued tasks
- Registered with Coral as local-file sources

### Configuration state (Files)
- `agents/*/` — gitagent-format agent definitions
- `kraken/voyages/*.yaml` — voyage templates
- `sources/*/` — custom Coral source specs

---

## Communication patterns

### Agent ↔ Agent: SQL Blackboard
Agents NEVER call each other directly. They communicate via writes/reads on `kraken.findings` and `kraken.plans`. This is stigmergic coordination — the same pattern as Hearsay-II and modern bMAS literature.

### Agent ↔ Coral: MCP stdio
Each agent has exactly one tool: `coral_sql(query: str)`. All data access flows through this.

### Agent ↔ External Actions: Composio MCP
For writes (create Linear ticket, draft PR, send email), agents use Composio MCP tools. This is the only place an agent touches a non-Coral API.

### UI ↔ Agent: AG-UI Protocol
CopilotKit's AG-UI protocol streams agent state, tool calls, and generative UI components from agents to the React frontend over Server-Sent Events + WebSocket.

### UI ↔ Supabase: Realtime Postgres
The Reef Map subscribes to `kraken.findings` changes via Supabase Realtime. Updates stream as agents write findings — no polling.

---

## Custom Coral source specs

Five custom sources extend Coral's coverage. Each is a Rust YAML manifest under `sources/<name>/manifest.yaml`.

### sources/osv/
- **Purpose:** OSV.dev vulnerability database
- **Auth:** None (public API)
- **Tables:** vulnerabilities, affected, ranges, references, aliases
- **Bounty:** $100 + $50 charity
- **Upstream PR target:** withcoral/coral

### sources/gmail/
- **Purpose:** Google Workspace Gmail
- **Auth:** OAuth2 (CustomAuth) — gmail.readonly scope
- **Tables:** messages, threads, labels, attachments
- **Critical:** Register Google Cloud OAuth client EARLY (verification delays can stretch days)
- **Bounty:** $100 + $50 charity

### sources/local-codebase/
- **Purpose:** Local filesystem as queryable SQL
- **Auth:** None (local)
- **Tables:** files (path, content, mtime), symbols (tree-sitter parsed), diffs (git log)
- **Backend:** tree-sitter bindings + libgit2
- **Bounty:** $100 + $50 charity

### sources/webhooks/
- **Purpose:** Real-time webhook deliveries as a table
- **Auth:** HMAC signature validation per-source
- **Tables:** deliveries (timestamp, source, payload), subscriptions
- **Backend:** Local HTTP receiver appends to JSONL; Coral reads as local-file source
- **Bounty:** $100 + $50 charity

### sources/kraken-graph/
- **Purpose:** Property graph backend for inferred relationships
- **Auth:** None (local)
- **Tables:** entities, relationships, paths
- **Backend:** KuzuDB (embeddable graph database, MIT)
- **Bounty:** $100 + $50 charity

---

## Observability architecture

Every Coral SQL call, every agent invocation, every LLM call emits OpenTelemetry spans following the GenAI semantic conventions. All spans flow to Langfuse via OTLP.

### Trace tree for a voyage execution

```
voyage_run (root)
├── quartermaster.plan
│   ├── reef_memory.recall  (LanceDB query, ~30ms)
│   └── llm.invoke          (Claude Opus 4.6, tokens: 800/200)
├── purser.execute_plan
│   ├── voyage.compile      (Jinja2, ~5ms)
│   ├── coral.sql           (12 sources, single plan, 9.2s)
│   │   ├── coral.source.gmail       (parallel, 800ms)
│   │   ├── coral.source.intercom    (parallel, 600ms)
│   │   ├── coral.source.stripe      (parallel, 400ms)
│   │   ├── coral.source.sentry      (parallel, 1.2s, CACHE HIT)
│   │   ├── coral.source.datadog     (parallel, 900ms)
│   │   ├── coral.source.github      (parallel, 1.5s)
│   │   └── coral.merge_and_join     (200ms)
│   ├── blackboard.write    (Parquet append, ~10ms)
│   └── llm.invoke          (synthesis, tokens: 1200/400)
└── quartermaster.synthesize
    ├── coral.sql (V8 self-ref) (200ms, CACHE HIT)
    ├── composio.draft_email  (Resend API, 300ms)
    ├── composio.draft_pr     (GitHub API, 500ms)
    └── composio.create_ticket (Linear API, 250ms)
```

### Custom span attributes
- `voyage.id` — correlation ID across the whole trace
- `voyage.name` — which YAML voyage executed
- `agent.name` — which crew member emitted the span
- `coral.sql.text` — the actual SQL (truncated to 500 chars)
- `coral.sql.sources` — list of source names referenced
- `coral.sql.cache_hit` — boolean per-source
- `coral.cost_usd_saved_vs_direct` — Bench-O-Bot's delta estimate

---

## Deployment topology

### Local development
- Coral: `coral mcp-stdio` subprocess
- Agents: Python process with CrewAI Flows
- UI: Next.js dev server on :3000
- Supabase: docker-compose, Postgres on :54322
- Langfuse: docker-compose on :3001
- PostHog: docker-compose on :8000
- Trigger.dev: docker-compose on :3030

### Single-binary distribution (stretch)
- All Python/TS/Rust components packaged via PyInstaller / pkg / cargo build
- Single executable: `kraken serve`
- Bundled SQLite for Supabase substitute in stretch demo

---

## Security architecture

### Threat model
- **Untrusted user input:** the Spyglass NL question. Sanitized before LLM injection.
- **Untrusted source data:** API responses. Validated against source spec schema before returning to agents.
- **Untrusted agent output:** LLM-generated SQL. Run through sqlglot AST validator before execution.
- **Secrets in transit:** All credentials in Supabase credential store, never in environment variables passed to Coral.
- **Secrets in logs:** Presidio + detect-secrets scrub all logged content before persistence.

### RLS policies (Supabase Postgres)
Every table has Row-Level Security policies:
- `voyage_runs.org_id = auth.jwt() ->> 'org_id'`
- `findings.org_id = auth.jwt() ->> 'org_id'`
- `audit_log.org_id = auth.jwt() ->> 'org_id'`

Demo moment: open two browser tabs with different orgs; verify isolation visually.

### Audit trail
Every agent action writes to an append-only Supabase table with PG cron-driven periodic snapshots to immudb (immutable database) for tamper-evidence.

---

## Failure modes and recovery

### LLM API failure
LiteLLM gateway fails over from Anthropic → OpenAI → Gemini → local Ollama (sqlcoder for SQL, llama3 for synthesis). Demo continues with degraded quality but never blanks.

### Coral subprocess failure
Health-check loop restarts Coral. In-flight voyages resume via DBOS replay from last checkpoint.

### Source API rate limit
Per-source leaky bucket rate limiter at the Coral layer. Voyages declare their rate-limit budget; scheduler respects it.

### Demo failure recovery
Hero demo path has a recorded fallback video. If the live demo fails, fall back to the recording with a clear "showing pre-recorded demo due to network issue" caption. Better than a frozen screen.

---

## Extension points

### Adding a new source
1. Create `sources/<name>/manifest.yaml` mirroring an existing bundled spec
2. Run `coral source test <name>`
3. Register in `kraken/coral_client.py` source list
4. Add fixture to `tests/sources/<name>/`
5. Document in `docs/sources/<name>.md`

### Adding a new voyage
1. Create `kraken/voyages/<name>.yaml` with SQL template, parameters, output schema
2. Add snapshot test in `tests/voyages/<name>_test.py`
3. Add Quartermaster routing rule in `agents/quartermaster/skills/routing.md`
4. Document in `docs/voyages/<name>.md` (auto-generated by `kraken voyage:docs`)

### Adding a new agent
1. Create `agents/<name>/` folder with SOUL.md, RULES.md, tools/coral.yaml, skills/
2. Register in `kraken/crew.py` agent registry
3. Add to AGENTS.md
4. Add tool schema documentation
