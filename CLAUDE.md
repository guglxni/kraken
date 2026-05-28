# CLAUDE.md — Vibecoding Constraints for KRAKEN

> This file is read first by Claude Code, Cursor, and any coding agent operating on this repo. It defines the hard constraints. Violations break the project's pitch.

---

## Project in one paragraph

KRAKEN is the canonical developer surface for Coral — a federated query platform that gives engineering organizations a single SQL interface over every system they run. Built for the WeMakeDevs "Pirates of the Coral-bean" hackathon, Track 1: Enterprise Agent. The pitch is that KRAKEN makes one Coral SQL query do what 5 SaaS products + 30 minutes of human triage currently do.

---

## Hard architectural rules

These are non-negotiable. Violating any of them breaks the pitch.

**Rule 1: Coral is the only data path for reads.** No agent calls Sentry directly. No agent calls GitHub directly. No agent calls any SaaS API directly. Every read operation is a `coral_sql()` call. If you find yourself importing `github` or `sentry` SDK clients in agent code, stop.

**Rule 2: Write actions go through Composio MCP, not Coral.** Reads = Coral SQL. Writes = Composio MCP tools (create Linear ticket, post Slack message, send email via Resend). This symmetry is part of the architectural story.

**Rule 3: All agent identities live in `agents/{name}/` folders in gitagent format.** No system prompts hardcoded in Python files. Every agent has `SOUL.md`, `RULES.md`, `tools/coral.yaml`, `skills/voyage-*.md`. CrewAI loads these at startup.

**Rule 4: Every voyage is a YAML file in `kraken/voyages/`.** No SQL inline in Python. Voyages compile via Jinja2 templating with parameters.

**Rule 5: All cross-agent state goes through `kraken.findings` (Parquet blackboard).** Agents never call each other directly. They write findings; other agents JOIN findings via Coral.

**Rule 6: No data leaves the laptop except (a) LLM API calls and (b) source API calls that Coral makes anyway.** No external telemetry beyond Langfuse self-hosted. No analytics SaaS. Local-first is the promise.

---

## Tech stack — what to use and what NOT to use

### USE
- **Python 3.12** for agents (CrewAI Flows + PydanticAI + DBOS)
- **TypeScript / Next.js 16 + React 19** for the UI (CopilotKit + assistant-ui + React Flow + Tremor + shadcn/ui)
- **Rust** ONLY for custom Coral source specs (osv, gmail, local-codebase, webhooks, kraken-graph)
- **DuckDB** for in-process analytics
- **LanceDB** for Reef Memory vector search
- **KuzuDB** for the property graph backend (kraken-graph source)
- **Supabase** for Auth + Postgres + Realtime + Storage
- **Trigger.dev** for scheduled jobs (morning briefing)
- **Langfuse self-hosted** for LLM observability
- **OpenInference / OpenTelemetry** for tracing
- **PostHog self-hosted** for product analytics on KRAKEN itself
- **Claude Opus 4.6** via Anthropic API (matches Coral's published benchmark)
- **LiteLLM** as the model gateway

### DO NOT USE
- **LangGraph** — we chose CrewAI Flows. Do not introduce LangGraph.
- **Redis** — Supabase Realtime + Postgres LISTEN covers all messaging needs.
- **Celery / Sidekiq** — Trigger.dev for scheduled, DBOS for durable.
- **gitclaw runtime** — gitagent is a file format only, not a runtime. Do not `npm install gitclaw` and call it from Python.
- **Composio for reads** — Composio is write-side only.
- **Any "claw" framework runtime** (OpenClaw, NullClaw, ZeroClaw, PicoClaw) — none of these are appropriate for this project.
- **GraphQL clients for source data** — Coral handles everything; no Apollo / urql in the agent layer.
- **Generic ORMs (SQLAlchemy, Prisma, Drizzle) for agent data access** — direct Coral SQL only.

---

## File structure

```
kraken/
├── README.md                    # Public-facing pitch
├── ARCHITECTURE.md              # System design (READ THIS SECOND)
├── PRD.md                       # Product requirements
├── AGENTS.md                    # Agent swarm specifications
├── DESIGN.md                    # Visual + UX design system
├── REQUIREMENTS.md              # Functional + non-functional reqs
├── PROPOSAL.md                  # Hackathon submission proposal
├── PLAN.md                      # Phased execution plan
├── SKILL.md                     # Reusable patterns + workflows
├── CLAUDE.md                    # THIS FILE
│
├── agents/                      # Gitagent-format agent definitions
│   ├── quartermaster/
│   │   ├── agent.yaml
│   │   ├── SOUL.md
│   │   ├── RULES.md
│   │   ├── tools/coral.yaml
│   │   └── skills/
│   ├── helm/                    # SRE specialist
│   ├── cooper/                  # Coding debugger
│   ├── bosun/                   # Sprint health
│   ├── purser/                  # Customer escalation
│   └── lookout/                 # Security & compliance
│
├── kraken/                      # Python agent runtime
│   ├── __init__.py
│   ├── crew.py                  # CrewAI Flows orchestration
│   ├── coral_client.py          # MCP client for Coral
│   ├── blackboard.py            # kraken.findings Parquet writer/reader
│   ├── reef_memory.py           # LanceDB vector search over past voyages
│   ├── bench.py                 # Bench-O-Bot Coral vs direct-MCP harness
│   ├── voyages/                 # Voyage YAML definitions
│   │   ├── hot_deploy.yaml
│   │   ├── incident_summary.yaml
│   │   ├── stuck_sprint.yaml
│   │   ├── angry_whales.yaml
│   │   ├── fresh_cve.yaml
│   │   ├── exec_escalation.yaml
│   │   ├── risk_heatmap.yaml
│   │   └── stigmergic_self_ref.yaml
│   └── cli.py                   # `kraken` CLI entrypoint (Click)
│
├── sources/                     # Custom Coral source specs (Rust YAML)
│   ├── osv/
│   ├── gmail/
│   ├── local-codebase/
│   ├── webhooks/
│   └── kraken-graph/
│
├── ui/                          # Next.js 16 frontend
│   ├── app/
│   │   ├── page.tsx             # Captain's Bridge home
│   │   ├── voyage-studio/       # Visual JOIN editor
│   │   ├── spyglass/            # Query trace inspector
│   │   ├── reef-map/            # Live causal graph
│   │   └── playground/          # Coral SQL REPL
│   ├── components/
│   ├── lib/
│   │   ├── copilotkit.ts
│   │   ├── supabase.ts
│   │   └── coral-mcp.ts
│   └── package.json
│
├── infra/                       # Self-hosted infrastructure
│   ├── docker-compose.yaml      # Supabase + Langfuse + PostHog + Trigger.dev
│   └── trigger/                 # Trigger.dev job definitions
│
├── tests/
│   ├── voyages/                 # Voyage snapshot tests
│   ├── sources/                 # Source spec tests (VCR fixtures)
│   └── e2e/                     # End-to-end demo path tests
│
└── docs/                        # Auto-generated voyage docs (Astro)
```

---

## Coding conventions

### Python
- **Type hints everywhere.** Use Pydantic for all agent handoff payloads.
- **No `Any` types.** If you reach for `Any`, restructure.
- **Async by default** in agent code. CrewAI Flows is async-native.
- **Error handling:** every Coral SQL call wrapped in a structured exception with the query text logged.
- **Logging:** structlog + OpenTelemetry. Every span has a `voyage_id` correlation ID.
- **Formatting:** ruff. Line length 100. Sort imports.

### TypeScript
- **Strict mode on.** No `any`, no implicit `any`, no `@ts-ignore`.
- **Server Components by default.** Client Components only when interactivity required.
- **Suspense + streaming** for all data fetches.
- **shadcn/ui** for primitives. Do not write a custom button.
- **Tremor** for charts and tables. Do not roll your own.
- **Formatting:** Biome (faster than ESLint+Prettier).

### Rust (source specs)
- **Mirror existing bundled specs exactly.** Read `withcoral/coral/sources/github/manifest.yaml` and `intercom/manifest.yaml` before writing new ones.
- **Run `make rust-checks` before every commit.**
- **Document every field in the YAML manifest.**

### SQL (voyages)
- **Always JOIN at least 3 Coral sources.** A voyage that touches one source is not a voyage.
- **Always include a date filter** in voyages over time-series sources (sentry, datadog, github.deployments) to keep result sets bounded.
- **Use window functions** (LAG, LEAD, ROW_NUMBER) for trend analysis.
- **Format SQL one clause per line.** SQL is documentation; readability matters.
- **No SELECT \*** in voyage definitions. Name every column explicitly.

---

## Testing requirements

- **Every voyage has a snapshot test.** Input: fixture data. Output: pinned result schema.
- **Every source spec has a VCR.py test recording.** Replay in CI.
- **Every agent has a prompt test** asserting it produces structured output matching its PydanticAI schema.
- **End-to-end demo test** runs the hero voyage (Acme churn) on every commit.
- **`make test` runs all of the above in under 90 seconds.**

---

## Demo path is sacred

The hero demo flow (hostile Gmail email → Reef Map renders → Spyglass shows the receipts → Bench-O-Bot compares) is the project's primary deliverable. Once the hero demo path is declared locked (typically once it's running end-to-end without flakiness), do not modify any code path that touches it without explicit approval. Add features in parallel; never on top of the demo path.

---

## Performance targets

- **Time to first token in chat:** under 2 seconds
- **Full voyage execution time:** under 30 seconds end-to-end
- **Reef Map first paint:** under 800ms
- **Coral SQL query latency (cached):** under 50ms
- **`kraken` CLI startup:** under 500ms
- **`make test`:** under 90 seconds
- **Docker compose up to working UI:** under 60 seconds on a fresh laptop

---

## Forbidden patterns

These will get caught in code review and judged harshly:

1. **Hardcoded API keys** anywhere. Use Supabase credential store or Infisical.
2. **Hardcoded source URLs** in agent code. Sources are defined in YAML; agents read them via `coral.tables`.
3. **`time.sleep()`** for any reason. Use proper async.
4. **`print()` statements** in production code paths. Use structlog.
5. **Mock data in `main` branch.** Test fixtures live in `tests/fixtures/`.
6. **TODOs in committed code** without GitHub issue references.
7. **Direct DOM manipulation** in React. Use refs sparingly; never `document.getElementById`.
8. **`useEffect` for data fetching.** Use React Query or Server Components.
9. **Inline styles.** Tailwind classes via shadcn/ui.
10. **Pirate slang in product copy.** Maritime terminology in the UI (Spyglass, Reef Map, Voyage Log). No "ahoy" or "matey" anywhere.

---

## When in doubt

1. Read `ARCHITECTURE.md` for system design questions.
2. Read `AGENTS.md` for agent behavior questions.
3. Read `PLAN.md` for "what should I work on next?"
4. Read `REQUIREMENTS.md` for spec questions.
5. Read `DESIGN.md` for UI/UX questions.
6. If still unclear, write the question into the PR description; do not guess.

---

## Vibecoding rules of engagement

When generating code in this repo:

- **Always read the relevant SOUL.md and RULES.md** for the agent you're modifying before editing its behavior.
- **Always read the relevant voyage YAML** before modifying its SQL.
- **Never modify the hero demo path** (voyages/exec_escalation.yaml + the Quartermaster routing for executive escalations) once it has been declared locked, unless explicitly instructed.
- **Never introduce a new dependency** without documenting why in the PR description.
- **Always add a test** when you add a feature. No exceptions.
- **Always update this file** when you discover a constraint that other agents will need to know.
