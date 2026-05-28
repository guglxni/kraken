# PRD.md — KRAKEN Product Requirements

> Product Requirements Document for KRAKEN, submitted to WeMakeDevs "Pirates of the Coral-bean" hackathon, Track 1: Enterprise Agent.

---

## Vision

KRAKEN is the canonical developer surface for Coral — a federated query platform that gives engineering organizations a single SQL interface over every system they run. It demonstrates that when you treat SQL-over-APIs as a primitive, the right architecture for the next generation of enterprise agents is a multi-agent swarm coordinating through cross-source JOINs, not a chatbot bolted onto N silos.

---

## Problem statement

The VP of Engineering at a mid-size SaaS company (50-500 engineers) runs a daily 09:00 ritual: open Linear, GitHub Insights, Sentry, Datadog, Slack, Intercom, PagerDuty, Confluence. Eight tabs. Twenty-five to forty minutes. Repeated before every staff meeting, board meeting, incident retro.

The current market response is five separate SaaS products, each owning one vertical:

| Vertical | Today's vendor | Structural limit |
|---|---|---|
| Coding-debug | Cursor + Sentry MCP | Sees code + errors; blind to revenue, sprint, vulnerabilities |
| AI SRE | Resolve.ai, incident.io, Rootly | Sees telemetry + tickets; blind to PR patterns, customer impact, OSV |
| Sprint health | Linear AI, Jira AI | Sees tickets; blind to runtime impact and customer signal |
| Customer escalation | Pylon, Intercom Fin | Sees inbox; blind to engineering reality |
| Security & compliance | Snyk, Dependabot, Vanta | Sees deps + policy; blind to deploy timing and customer blast radius |

The structural defect: each vendor is a chatbot over its own warehouse. None can execute the JOIN that the VP-Eng's brain executes manually every morning. Coral's read-layer-as-SQL primitive is the first technology that makes that JOIN executable by an agent, locally, in one query, with caching, with no ETL, with no data leaving the laptop.

---

## Target users

### Primary persona — Platform Engineering Lead
- Title: Head of Platform, Director of Platform Engineering, or VP Engineering at 50-500 person SaaS
- Pain: Spends 30+ min/day stitching context across 8+ tools
- Budget authority: Owns the line item for incident response tooling and observability
- Decision criterion: "Can this give my team faster MTTR and free them from tab-switching?"

### Secondary persona — On-call Engineer
- Title: Senior/Staff Software Engineer with on-call rotation
- Pain: Paged at 3 AM, must reconstruct what shipped, who's affected, what's broken
- Decision criterion: "Does this make me effective faster than the current runbook?"

### Tertiary persona — Engineering Manager
- Pain: Sprint health visibility without micromanaging
- Decision criterion: "Does this surface blockers I'd otherwise miss?"

### Explicitly NOT target
- Individual contributor engineers (Cursor + Sentry MCP own this seat)
- Incident commanders at large enterprises (Resolve.ai, incident.io own this)
- Compliance officers (Vanta, Drata own this)

---

## Category positioning

**KRAKEN is a read-only operating picture for engineering leaders.**

- Not incident management (we hand off to PagerDuty and Linear)
- Not observability (we read Datadog and Grafana; we don't store metrics)
- Not a coding agent (we draft PRs; humans merge)
- Not a chat-ops bot (we don't run interactive Slack workflows)

We are the layer that sits above all five verticals and answers cross-domain questions in one Coral SQL plan.

---

## Core features (P0 — required for submission)

### F1. Spyglass — natural language query interface
- Chat UI with streaming responses
- AG-UI protocol via CopilotKit
- Generative UI for results (tables, charts, alert cards)
- History persisted to Supabase

### F2. Reef Map — live causal graph
- React Flow rendering of agent tool-call traces
- Nodes: sources, entities (PRs, incidents, customers, CVEs)
- Edges: the JOIN relationships
- Real-time updates via Supabase Realtime
- Time-scrub replay of past voyages

### F3. Voyage Studio — visual JOIN editor
- Drag-and-drop sources from palette
- Draw JOIN lines; system infers compatible keys
- Monaco editor showing compiled SQL in real-time
- Schema autocomplete from `coral.tables` / `coral.columns`
- Export as voyage YAML

### F4. Coral Playground — SQL REPL
- Monaco editor with schema-aware autocomplete
- Run arbitrary Coral SQL
- Results in sortable Tremor table
- NL-to-SQL via sqlcoder on Ollama
- Shareable query URLs

### F5. Multi-agent swarm — six specialists
- Quartermaster (planner)
- Helm (SRE)
- Cooper (coding debugger)
- Bosun (sprint health)
- Purser (customer escalation)
- Lookout (security & compliance)
- All defined in gitagent format
- Coordinated via SQL blackboard

### F6. Voyage library — eight cross-source queries
- Hot Deploy (V1)
- Incident Auto-Summary (V2)
- Stuck Sprint (V3)
- Angry Whales (V4)
- Fresh CVE in Production (V5)
- Executive Escalation (V6)
- Risk Heatmap (V7)
- Stigmergic Self-Reference (V8)

### F7. Custom Coral source specs — five built
- osv (vulnerability database)
- gmail (email)
- local-codebase (filesystem + git)
- webhooks (real-time events)
- kraken-graph (property graph via KuzuDB)

### F8. Bench-O-Bot — measurable Coral advantage
- Side-by-side comparison of Coral MCP vs. direct provider MCPs
- Measures latency, token count, cost, accuracy
- Renders reproduction of Coral's published 31% / 3.4× / 42% numbers

### F9. Reef Memory — query learning loop
- Every successful voyage embedded into LanceDB
- Top-3 similar past voyages retrieved as few-shot exemplars
- Second-run cost/latency reduction demonstrated

### F10. CLI — terminal-first interface
- `kraken voyage:run NAME`
- `kraken voyage:compile`
- `kraken voyage:test`
- `kraken voyage:lint`
- `kraken voyage:docs`
- `kraken source:forge --openapi PATH`
- `kraken bench --voyage NAME`

---

## Important features (P1 — strongly desired)

### F11. Source Spec Forge
- OpenAPI 3.1 → Coral YAML auto-generation
- GraphQL schema → Coral YAML
- Curl command → Coral YAML (via curlconverter)
- Spec linter with semgrep rules
- Spec test harness via VCR.py

### F12. Voyage compiler
- Jinja2 parameter injection
- Output schema validation
- Snapshot testing
- Static analysis via sqlglot

### F13. Auth + multi-tenancy
- Supabase Auth (Google/GitHub/Slack/Linear/Notion OAuth)
- Postgres RLS per-org isolation
- Demo: two browser tabs, two orgs, isolated data

### F14. Notification + action layer
- Composio MCP for write actions
- Knock/Novu for notification routing
- Resend for transactional email (live in demo)

### F15. Scheduled jobs
- Trigger.dev for morning briefing (08:30 cron)
- Event-driven triggers (deploy → Hot Deploy voyage)
- Retry semantics with exponential backoff

### F16. Observability stack
- Langfuse self-hosted for LLM traces
- OpenInference instrumentation everywhere
- PostHog self-hosted for product analytics
- Self-referential closure: query PostHog via Coral

### F17. Voyage docs auto-generation
- `kraken voyage:docs` produces Astro static site
- Every voyage: SQL, parameters, output schema, consumers
- Lineage graph via OpenLineage

### F18. Auto-generated client SDKs
- Python, TypeScript, Go SDKs
- Generated from FastAPI OpenAPI spec via openapi-generator
- Published to PyPI / npm / pkg.go.dev (stretch)

---

## Nice-to-have features (P2 — if time permits)

- F19. Real-time collaborative voyage editing (Yjs)
- F20. Voice interface (OpenAI Realtime API)
- F21. Slack bot integration (Bolt for Python)
- F22. Embeddable web component (`<kraken-voyage>`)
- F23. Apache Iceberg time-travel on `kraken.findings`
- F24. Differential privacy on aggregations (OpenDP)
- F25. SAST on voyage SQL (semgrep)
- F26. Hallucination detection on agent outputs (Lynx/selfcheckgpt)
- F27. Compliance evidence auto-generation (SOC 2 / ISO 27001)
- F28. Edge deployment via Cloudflare Workers / Fly.io

---

## Out of scope

These are explicitly NOT part of KRAKEN:

- Storage of source data (Coral handles read-through caching only)
- Real-time alerting infrastructure (we hand off to PagerDuty)
- Incident command/control workflows (we hand off to incident.io)
- IDE plugins (we are not Cursor)
- Hosted SaaS deployment (we are local-first; SaaS is post-hackathon)
- Mobile apps (web only)
- Multi-region replication (single-laptop deployment is the promise)
- Voice cloning / TTS beyond the F20 stretch

---

## Success metrics

### Demo metrics (must hit on stage)
- Hero voyage executes in under 15 seconds end-to-end
- Bench-O-Bot shows ≥20% latency reduction vs. direct MCP
- Bench-O-Bot shows ≥2× cost reduction vs. direct MCP
- Reef Map renders within 800ms of voyage start
- Zero failed Coral queries during the demo

### Project quality metrics (judged via repo)
- 23 Coral sources connected (21 bundled + 5 custom — 26 total, 5 custom for bounties)
- 8 voyage queries all cross-source (4+ sources each)
- 6 specialist agents in gitagent format
- 100% of agent reads through `coral_sql()`
- `make test` passes in under 90 seconds
- README installation works on a fresh laptop in under 5 minutes

### Hackathon-specific metrics
- Track 1 first place
- 5× custom source spec bounty ($500 + $250 charity total)
- "Best Use of Coral" criterion: ceiling score
- Discord showcase featured in top 50 (Claude Max vouchers)
- "Best Guide" prize via reproducible blog post

---

## User stories

### As a Platform Lead on Monday morning
- I open KRAKEN and see the Risk Heatmap (V7) showing what's burning
- I click into a high-weight incident card; the Reef Map renders the full causal context
- I draft a CEO reply via Anchor approval; KRAKEN sends it via Resend
- I share the voyage URL with my team for context

### As an On-call Engineer paged at 3 AM
- I run `kraken voyage:run incident-summary --id=PD-12345` from terminal
- KRAKEN returns a 4-bullet summary with deploy correlation in 9 seconds
- I see which PR caused it, who authored it, what % of customers are affected
- I draft the rollback PR via Cooper's Composio integration

### As an Engineering Manager reviewing sprint health
- I ask Spyglass "what's blocked in this sprint?"
- Bosun runs the Stuck Sprint voyage (V3)
- I see 4 issues stuck >3 days with their open PRs, Slack mentions, spec docs
- I create Linear comments via Anchor approval

### As a Security Engineer post-CVE-disclosure
- I ask "what new high-severity CVEs landed in our prod deps in the last 7 days?"
- Lookout runs the Fresh CVE voyage (V5) via OSV custom source
- I see CVE → affected package → dependency in repo → deploy that introduced it → author
- I file a security issue via Linear with full context

### As the hackathon judge evaluating Track 1
- I clone the repo and run `docker compose up`
- In under 60 seconds the Captain's Bridge is live at localhost:3000
- I run the hero demo via a pre-seeded fixture
- I read PROPOSAL.md, see the architectural thesis, evaluate each judging criterion
- I award Track 1 first place

---

## Constraints

- **Time:** hackathon build window plus a Foundation phase for scaffolding
- **Team:** 4 person team max (per hackathon rules)
- **Budget:** $0 (FOSS only, plus generous free tiers)
- **Deployment:** Local-first; no cloud-required dependencies for the demo
- **Data:** No proprietary data in the public repo; test fixtures only

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gmail OAuth verification delays demo | Medium | High | Pre-register OAuth client at the start of the Foundation phase, use testing-mode users |
| Coral early-stage bugs in bundled sources | Medium | Medium | Budget half-day at start for source-spec workarounds |
| 5-voyage scope is too much | High | Medium | Cut list in PLAN.md; hero demo (V6) stands alone |
| Reef Map auto-layout looks tangled | Medium | High | Hand-tune layouts for demo; use Mermaid fallback |
| Bench-O-Bot numbers don't match Coral's | High | Medium | Frame as "our workload measured X/Y/Z" not as "we replicated" |
| Multi-agent coordination overhead bites | Medium | Medium | Drop polling, use direct CrewAI handoffs for findings retrieval |
| DBOS+Postgres adds setup complexity | Medium | Low | Fall back to in-memory state for hackathon; ship DBOS post-event |

---

## Out-of-scope decisions already made

- **CrewAI Flows, not LangGraph** — see CLAUDE.md for reasoning
- **gitagent file format, not gitclaw runtime** — file format only
- **Python for agents, TypeScript for UI, Rust for source specs** — polyglot is correct
- **Coral-only reads, Composio-only writes** — architectural symmetry
- **No "claw" framework runtimes** (OpenClaw, NullClaw, etc.) — wrong category
- **No LangChain at all** — CrewAI's role abstraction is sufficient

---

## Open questions for the team

1. Do we ship the kraken-graph source as a P0 or P1? (Currently P0; could drop to P1 if time crunched)
2. Voice interface (F20) — yes/no for the demo? (Currently P2)
3. Slack bot (F21) — does it strengthen the demo or distract? (Currently P2)
4. Edge deployment story (F28) — necessary or noise? (Currently P2; skip for hackathon)
