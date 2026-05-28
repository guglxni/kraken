# REQUIREMENTS.md — KRAKEN Technical Requirements

> Functional and non-functional requirements. Every requirement has an ID for traceability. P0 = must ship for hackathon; P1 = strongly desired; P2 = nice-to-have.

---

## Functional requirements

### FR-001 (P0): Federated SQL query execution
The system shall accept a SQL query referencing any combination of connected Coral sources and return a unified result set in a single execution plan.

**Acceptance:** A query JOINing `github.pulls × sentry.issues × stripe.subscriptions` returns rows within 30 seconds when run against fixture data.

### FR-002 (P0): Six specialist agents
The system shall provide six agents (Quartermaster, Helm, Cooper, Bosun, Purser, Lookout) each defined in gitagent format and orchestrated via CrewAI Flows.

**Acceptance:** Each agent loads from `agents/<name>/` folder, accepts plans from `kraken.plans`, writes findings to `kraken.findings`.

### FR-003 (P0): Eight voyage queries
The system shall ship eight production-quality cross-source SQL voyages in `kraken/voyages/`, each touching 4+ Coral sources.

**Acceptance:** Running `kraken voyage:run NAME` for each voyage returns rows from fixture data; output schema matches declared contract.

### FR-004 (P0): Five custom Coral source specs
The system shall ship five custom source specs: `osv`, `gmail`, `local-codebase`, `webhooks`, `kraken-graph`.

**Acceptance:** Each spec passes `coral source test NAME`. Each is documented and ready for upstream PR submission.

### FR-005 (P0): SQL blackboard coordination
Agents shall coordinate exclusively through `kraken.findings` and `kraken.plans` tables exposed as local-file Coral sources.

**Acceptance:** No agent code imports another agent's module. All inter-agent state flows through Coral SQL reads/writes.

### FR-006 (P0): Natural language interface (Spyglass)
The system shall provide a chat interface that accepts natural-language questions and routes them to appropriate voyages.

**Acceptance:** Typing "why is Acme churning?" triggers the Executive Escalation voyage and renders a 4-bullet summary within 15 seconds.

### FR-007 (P0): Live causal graph (Reef Map)
The system shall render a React Flow graph showing the entities and JOIN relationships used by an active voyage, updating in real-time as agents write findings.

**Acceptance:** During the hero demo, the Reef Map animates 8+ nodes with edges within 5 seconds of voyage start.

### FR-008 (P0): Coral SQL playground
The system shall provide a SQL REPL with schema-aware autocomplete from `coral.tables` and `coral.columns`.

**Acceptance:** Typing `SELECT * FROM github.` shows a dropdown of all github tables with column previews.

### FR-009 (P0): Bench-O-Bot comparison
The system shall run identical queries via Coral MCP and direct provider MCPs, measuring latency, token count, cost, and accuracy.

**Acceptance:** Bench panel renders side-by-side comparison showing Coral advantage on the hero voyage.

### FR-010 (P0): Reef Memory learning loop
The system shall embed every successful voyage and retrieve top-3 similar past voyages as few-shot exemplars for new queries.

**Acceptance:** Second execution of the same voyage class shows measurably lower latency or cost than the first.

### FR-011 (P0): CLI interface
The system shall provide a `kraken` CLI with subcommands: `voyage:run`, `voyage:compile`, `voyage:test`, `voyage:lint`, `voyage:docs`, `source:forge`, `source:lint`, `source:test`, `bench`.

**Acceptance:** Each subcommand has `--help` output and exits 0 on success, non-zero on failure.

### FR-012 (P0): Anchor approval gate
The system shall require explicit user approval before executing any write action (email send, PR draft submission, Linear ticket creation, PagerDuty page).

**Acceptance:** No Composio MCP write tool fires without a click on an Anchor approval button.

### FR-013 (P1): Voyage Studio (visual JOIN editor)
The system shall provide a drag-and-drop visual editor for composing cross-source SQL queries.

**Acceptance:** A user can drag two sources onto a canvas, draw a JOIN line, and see compiled SQL appear in real-time.

### FR-014 (P1): Source Spec Forge
The system shall generate Coral YAML source specs from OpenAPI 3.1, GraphQL schemas, or curl commands.

**Acceptance:** Pasting an OpenAPI spec for the Stripe API produces a working Coral source spec that passes `coral source test`.

### FR-015 (P1): Voyage compiler
The system shall compile voyage YAML templates into executable SQL via Jinja2 with parameter validation.

**Acceptance:** `kraken voyage:compile hot-deploy --hours-back=12` produces SQL with the parameter substituted.

### FR-016 (P1): Voyage snapshot testing
The system shall support snapshot tests that pin voyage output schemas and detect breaking changes.

**Acceptance:** Modifying a voyage's SQL in a way that changes output schema causes the snapshot test to fail with a clear diff.

### FR-017 (P1): Voyage lint
The system shall analyze voyage SQL for unused JOINs, missing date filters, and high-cost patterns.

**Acceptance:** `kraken voyage:lint stuck-sprint` reports any issues with specific line numbers and suggested fixes.

### FR-018 (P1): Auto-generated voyage docs
The system shall produce a static documentation site (Astro) from voyage YAML metadata.

**Acceptance:** `kraken voyage:docs` generates a deployable site with one page per voyage showing SQL, sources, parameters, output schema.

### FR-019 (P1): Supabase auth integration
The system shall use Supabase Auth for OAuth flows to all source APIs requiring authentication.

**Acceptance:** Connecting Gmail goes through Supabase's verified OAuth flow with no "unverified app" red screen during demo.

### FR-020 (P1): Row-level security
The system shall enforce per-organization data isolation via Postgres RLS on all multi-tenant tables.

**Acceptance:** Two browser sessions with different org IDs see disjoint datasets even when querying the same table.

### FR-021 (P1): Scheduled morning briefing
The system shall execute the Risk Heatmap voyage at 08:30 daily via Trigger.dev and post results to Slack.

**Acceptance:** Trigger.dev dashboard shows successful daily runs; corresponding Slack messages appear.

### FR-022 (P1): Durable agent execution
The system shall persist agent execution state via DBOS, supporting crash recovery and time-travel debugging.

**Acceptance:** Killing the agent process mid-voyage and restarting allows the voyage to resume from the last checkpoint.

### FR-023 (P1): End-to-end observability
The system shall emit OpenTelemetry spans for every Coral SQL call, agent invocation, and LLM call, with `voyage_id` correlation across the trace tree.

**Acceptance:** A single voyage trace in Langfuse shows the full nested span tree from UI request to final synthesis.

### FR-024 (P1): Notification routing
The system shall route alerts via Knock or Novu, supporting Slack, email, SMS, and in-app channels.

**Acceptance:** A critical CVE detected by Lookout fires notifications to all configured channels for that severity.

### FR-025 (P1): Real-time UI updates
The Reef Map shall update without polling via Supabase Realtime subscriptions to `kraken.findings`.

**Acceptance:** Writing a finding from a CLI command causes the open Reef Map UI to update within 1 second.

### FR-026 (P2): Public REST + GraphQL API
The system shall expose voyage execution via FastAPI REST and strawberry-graphql endpoints.

### FR-027 (P2): SDK generation
The system shall auto-generate client SDKs for Python, TypeScript, and Go from the OpenAPI spec.

### FR-028 (P2): Slack bot integration
The system shall support running voyages from Slack via slash commands.

### FR-029 (P2): Voice interface
The system shall support voice input via the OpenAI Realtime API for hands-free operation.

### FR-030 (P2): Real-time collaborative voyage editing
The system shall support multi-user concurrent editing of voyage YAML via Yjs CRDTs.

---

## Non-functional requirements

### NFR-001 (P0): Performance — voyage execution latency
The hero voyage shall execute end-to-end in under 15 seconds (LLM time included) on a baseline laptop (M3 Pro or equivalent).

**Acceptance:** Five consecutive timed runs of `kraken voyage:run exec-escalation` complete in under 15s wall-clock each.

### NFR-002 (P0): Performance — UI responsiveness
Time to first token in Spyglass chat shall be under 2 seconds from query submission.

**Acceptance:** Lighthouse performance audit shows TTFB < 200ms and FCP < 1.5s on the Captain's Bridge home page.

### NFR-003 (P0): Performance — Coral cached query latency
Repeat queries hitting the Coral cache shall return in under 50ms.

**Acceptance:** Re-running the same voyage within 60 seconds shows >90% cache hit rate in Spyglass.

### NFR-004 (P0): Reliability — zero data egress
No data from connected sources shall leave the user's machine except through (a) direct LLM API calls and (b) the same source APIs Coral would call anyway.

**Acceptance:** Network monitoring during a full demo run shows traffic only to anthropic.com, source APIs, and configured infrastructure endpoints (Supabase, Langfuse).

### NFR-005 (P0): Setup — installation time
A fresh laptop shall reach a working Captain's Bridge UI in under 60 seconds via `docker compose up`.

**Acceptance:** Stopwatch test on a wiped MacBook completes in <60s including container pulls.

### NFR-006 (P0): Setup — README reproducibility
Following the README installation steps shall produce a working KRAKEN deployment in under 5 minutes including manual configuration.

**Acceptance:** A second team member follows the README on a clean machine and reports success in <5 min.

### NFR-007 (P0): Code quality — test coverage
The test suite shall pass `make test` in under 90 seconds and cover all 8 voyages, all 6 agents, and all 5 source specs.

**Acceptance:** `make test` exits 0 in <90s. `make coverage` shows >80% line coverage on `kraken/` package.

### NFR-008 (P0): Code quality — type safety
All Python code shall pass `mypy --strict`. All TypeScript code shall pass `tsc --noEmit` with strict mode.

**Acceptance:** CI pipeline runs both checks and fails on any error.

### NFR-009 (P0): Security — no hardcoded secrets
No API keys, OAuth client secrets, or credentials shall appear in the repository.

**Acceptance:** `detect-secrets scan` returns zero high-confidence findings on the main branch.

### NFR-010 (P0): Security — input validation
All natural-language queries shall be sanitized before LLM injection. All agent-generated SQL shall pass sqlglot AST validation before Coral execution.

**Acceptance:** SQL injection attempts in Spyglass do not execute against Coral.

### NFR-011 (P1): Observability — trace completeness
Every voyage execution shall produce a complete OpenTelemetry trace tree linking UI request → agent invocation → Coral SQL → source API → response.

**Acceptance:** Picking any voyage in Langfuse shows the full nested trace with timing per span.

### NFR-012 (P1): Reliability — graceful degradation
Failure of any single source API shall not block voyages that don't depend on that source. The LLM API shall fail over from Anthropic → OpenAI → Gemini → local Ollama.

**Acceptance:** Manually breaking the GitHub source API does not prevent the Stuck Sprint voyage (which uses Linear) from completing.

### NFR-013 (P1): Multi-tenancy — data isolation
Postgres RLS policies shall enforce per-org isolation on all tables containing org-scoped data.

**Acceptance:** Demo with two browser sessions and different org IDs shows zero data crossover.

### NFR-014 (P1): Audit trail — immutability
Every agent action shall be logged to an append-only audit trail with timestamps, agent identity, and action payload.

**Acceptance:** Querying `audit_log` in Supabase returns the full sequence of actions for any voyage_id.

### NFR-015 (P1): Documentation — every public function
Every public function in `kraken/` and exported function in `ui/` shall have a docstring or JSDoc describing parameters, return values, and side effects.

**Acceptance:** `pydoc kraken` and TypeDoc generate complete documentation with no missing entries.

### NFR-016 (P1): Maintainability — voyage portability
Voyages shall be runnable independent of the CrewAI orchestration via the `kraken` CLI.

**Acceptance:** `kraken voyage:run NAME` works without any agent layer running.

### NFR-017 (P2): Performance — concurrent voyages
The system shall support running 5 concurrent voyages without degraded latency on a baseline laptop.

**Acceptance:** 5 parallel `kraken voyage:run` invocations all complete in under 30s.

### NFR-018 (P2): Scalability — voyage library growth
The voyage compiler shall handle 100+ voyage YAML files without measurable performance degradation.

**Acceptance:** `kraken voyage:compile` runs in <2s with 100 voyages in the directory.

---

## Demo requirements

### DR-001: Demo video
The submission shall include a demo video that:
- Opens with the hackathon name ("Pirates of the Coral-bean — KRAKEN by [team]")
- Shows the hero voyage end-to-end in under 90 seconds
- Displays the Bench-O-Bot comparison with Coral's published benchmark numbers as a reference frame
- Shows at least three other voyages in a montage
- Includes the GitHub repo URL in the final frame

### DR-002: Reproducible blog post
The submission shall include a 2-3 page blog post that:
- Walks through building KRAKEN with reproducible code snippets
- Covers all 5 custom source specs
- Demonstrates the cross-source JOIN pattern with at least one full voyage
- Qualifies for the "Best Guide" Keychron prize

### DR-003: Discord showcase
The submission shall include a post in the Coral Discord `#how-i-coral` channel with:
- Screenshots of the Captain's Bridge
- A short writeup of the architectural thesis
- Cross-posted to LinkedIn and X tagging @withcoral

### DR-004: Custom source spec PRs
The submission shall include upstream PRs to `withcoral/coral` for:
- `osv` source spec
- `gmail` source spec
- `local-codebase` source spec
- `webhooks` source spec
- `kraken-graph` source spec

Each PR shall be merge-ready: tests passing, documentation included, conforming to bundled spec conventions.

---

## Dependencies

### Critical-path dependencies (failure blocks demo)
- Coral v0.1.3 or later (Apache 2.0)
- Claude Opus 4.6 API access (Anthropic)
- Supabase (self-hosted via docker-compose)
- Node.js 24+ and Python 3.12+ on demo machine

### Important dependencies (failure degrades demo)
- Langfuse self-hosted
- PostHog self-hosted
- Trigger.dev self-hosted
- Local Ollama with sqlcoder for NL-to-SQL fallback

### Nice-to-have dependencies
- Resend API key for live email sending
- Composio MCP for write actions
- KuzuDB embedded for kraken-graph source

---

## Constraints

### Time
- Hackathon build window with a Foundation phase for scaffolding
- Demo video for submission (kept short per hackathon convention)

### Team
- 4 person team maximum (per hackathon rules)
- Each member gets full prize if team wins (no splitting)

### Budget
- $0 cash budget — FOSS dependencies only
- LLM API costs estimated at <$50 across the build (use Claude Code's existing access)

### Compatibility
- MacOS, Linux, Windows (WSL) supported
- Docker required for infrastructure containers
- Modern browser (Chrome 130+, Safari 19+, Firefox 130+) for UI

### Legal
- All FOSS dependencies must be OSI-approved licenses (MIT, Apache 2.0, BSD, LGPL acceptable; GPL avoided)
- KRAKEN itself shall be Apache 2.0
- No proprietary data in the public repo

---

## Definition of done

A feature is "done" when:
1. Implemented in code with type safety
2. Unit tested with >80% line coverage
3. Snapshot tested if it produces structured output
4. Documented (docstring/JSDoc minimum)
5. Wired into the CLI or UI as appropriate
6. Observable via Langfuse trace
7. Reviewed against CLAUDE.md constraints
8. Merged to main with green CI

A voyage is "done" when:
1. YAML definition in `kraken/voyages/` with parameters and output schema
2. SQL passes `kraken voyage:lint`
3. Snapshot test in `tests/voyages/` passes
4. Routing rule added to Quartermaster's `routing.md`
5. Documented page generated by `kraken voyage:docs`
6. End-to-end run from CLI completes in under 30 seconds

A source spec is "done" when:
1. Rust YAML manifest in `sources/<name>/manifest.yaml`
2. `coral source test NAME` passes
3. VCR.py fixture test in `tests/sources/<name>/`
4. Documentation page in `docs/sources/<name>.md`
5. Upstream PR opened against `withcoral/coral`
