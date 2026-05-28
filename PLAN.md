# PLAN.md — KRAKEN Phased Execution Plan

> Phase-based execution plan for KRAKEN. Phases are sequenced by dependency, not by calendar. Each phase has explicit exit criteria. Decision thresholds with concrete fallback paths are documented for behind-schedule scenarios. Cut list is prioritized so the demo path survives even at maximum scope reduction.

---

## Phase model

KRAKEN is built in three macro-phases, each containing several sub-phases. Macro-phases must complete in order. Sub-phases within a macro-phase can be parallelized across team members.

```
┌───────────────────────────────────────────────────────────┐
│ MACRO-PHASE 1: FOUNDATION                                  │
│  ├── 1.1  Repo scaffolding                                 │
│  ├── 1.2  Coral integration                                │
│  ├── 1.3  Source spec preparation                          │
│  ├── 1.4  Frontend scaffolding                             │
│  ├── 1.5  Agent scaffolding                                │
│  ├── 1.6  Voyage draft                                     │
│  └── 1.7  Infrastructure stack                             │
└───────────────────────┬───────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────┐
│ MACRO-PHASE 2: BUILD                                       │
│  ├── 2.1  End-to-end thinnest slice (hero voyage)         │
│  ├── 2.2  All voyages running                              │
│  ├── 2.3  UI polish + Reef Map                             │
│  ├── 2.4  Custom source specs complete                     │
│  ├── 2.5  Reef Memory + learning loop                      │
│  └── 2.6  Bench-O-Bot + observability                      │
└───────────────────────┬───────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────┐
│ MACRO-PHASE 3: SUBMISSION                                  │
│  ├── 3.1  Demo recording                                   │
│  ├── 3.2  Blog post                                        │
│  ├── 3.3  Discord + social showcase                        │
│  ├── 3.4  Upstream source spec PRs                         │
│  └── 3.5  Final polish + entry submission                  │
└───────────────────────────────────────────────────────────┘
```

---

## Macro-phase 1: Foundation

The goal of Foundation is to have every component scaffolded such that subsequent phases only add functionality, not infrastructure. Foundation is "complete" when the thinnest possible end-to-end smoke test passes.

### Phase 1.1 — Repo scaffolding

Set up the monorepo structure per CLAUDE.md. Establish toolchains for Python (uv or poetry), TypeScript (pnpm), and Rust (cargo). Configure CI on GitHub Actions with placeholder jobs. Land all nine vibecoding docs (CLAUDE, ARCHITECTURE, PRD, AGENTS, DESIGN, REQUIREMENTS, PROPOSAL, PLAN, SKILL) in the repo root.

**Exit criterion:** Repo skeleton exists; `make test` passes with placeholder tests; CI green; all docs landed.

### Phase 1.2 — Coral integration

Install Coral CLI. Get `coral mcp-stdio` talking to a coding agent. Add 5 bundled sources with disposable test workspaces (GitHub fixture repo, Sentry dev project, Slack test workspace, Linear test workspace, Stripe test mode). Write the thinnest possible `kraken/coral_client.py` that wraps the MCP stdio transport.

**Exit criterion:** `coral_sql("SELECT * FROM github.repos LIMIT 1")` from Python returns rows.

### Phase 1.3 — Source spec preparation

Read OSV.dev and Gmail API docs end-to-end. Register Google Cloud OAuth client immediately at the start of this phase since verification can take days. Draft `sources/osv/manifest.yaml` and `sources/gmail/manifest.yaml` (scaffolding only; full implementation comes in Phase 2.4). Set up VCR.py test fixtures for both.

**Exit criterion:** OAuth client ID + secret in Supabase credential store; OSV manifest validates against bundled spec grammar.

### Phase 1.4 — Frontend scaffolding

Bootstrap Next.js 16 + shadcn/ui + Tailwind v4. Add CopilotKit with `<CopilotChat>`. Add assistant-ui shell. Add React Flow with placeholder canvas. Add Tremor with sample dashboard. Wire Supabase Auth (Google + GitHub providers).

**Exit criterion:** Captain's Bridge home page renders with chat input, empty Reef Map, and voyage library skeleton.

### Phase 1.5 — Agent scaffolding

Create `agents/` folder structure with all 6 agents in gitagent format. Write SOUL.md and RULES.md for each (use AGENTS.md as source). Write `kraken/crew.py` with CrewAI Flows loading the gitagent definitions. Implement blackboard read/write helpers in `kraken/blackboard.py`.

**Exit criterion:** `python -m kraken.crew --agent quartermaster --prompt "test"` produces a structured response.

### Phase 1.6 — Voyage draft

Write all 8 voyage YAML files in `kraken/voyages/`. Each parses; SQL may have placeholder logic. Set up Jinja2 templating in `kraken/voyages/compiler.py`. Hand-write the V6 (Executive Escalation) hero voyage to be 100% ready since it's the demo headliner.

**Exit criterion:** `kraken voyage:compile exec-escalation` produces valid SQL.

### Phase 1.7 — Infrastructure stack

docker-compose with Supabase, Langfuse, PostHog, Trigger.dev. Wire DBOS Transact to Supabase Postgres. Wire OpenInference instrumentation through CrewAI. Smoke-test the full stack.

**Exit criterion:** `docker compose up` brings the stack online in <60s; a trace from a test agent run appears in Langfuse.

---

## Macro-phase 2: Build

The goal of Build is functional completeness against the P0 feature set. Build is "complete" when every voyage runs end-to-end, every source spec passes tests, and the Bench-O-Bot harness produces reproducible numbers.

### Phase 2.1 — End-to-end thinnest slice

Wire V6 (Executive Escalation) from Spyglass → Quartermaster → Purser → Coral SQL → Supabase write → UI render. Hook up Reef Map to render the JOIN graph for V6. Make `osv` and `gmail` sources fully working (not just scaffolded). Pre-record OAuth flows so the demo doesn't perform OAuth live.

**Exit criterion:** Typing "Why is Acme churning?" in Spyglass returns a structured answer with Reef Map populated in <30 seconds.

**Decision threshold:** If end-to-end exceeds 30 seconds → drop the Reef Memory call (Phase 2.5 work); ship V6 without exemplar injection.

### Phase 2.2 — All voyages running

Wire all 5 specialist agents executing their voyages end-to-end:
- V1 (Hot Deploy) through Cooper with local-codebase source
- V2 (Incident Summary) through Helm
- V3 (Stuck Sprint) through Bosun
- V4 (Angry Whales) through Purser
- V5 (Fresh CVE) through Lookout with OSV source

Each voyage: hardcoded prompt input, JSON output, snapshot test passing.

**Exit criterion:** `kraken voyage:run NAME` works for all 5 P0 voyages with fixture data.

**Decision threshold:** If any voyage exceeds 90 seconds → simplify the SQL (fewer JOINs) or move to fixture data only.

### Phase 2.3 — UI polish + Reef Map polish

Build Voyage Studio (visual JOIN editor) — minimum viable: drag two sources, draw a line, see SQL. Build Spyglass query trace inspector (Crow's Nest panel). Build Bench-O-Bot side-by-side comparison panel. Hand-tune Reef Map node positions for the V6 hero flow. Wire Supabase Realtime so Reef Map updates without polling.

**Exit criterion:** Hero demo path is visually compelling. Reef Map animates smoothly. Voyage Studio renders without bugs.

**Decision threshold:** If Voyage Studio drag-and-drop is fighting React Flow → ship it as a read-only viewer with a "build mode coming soon" badge; lose 1 P1 point.

### Phase 2.4 — Custom source specs complete

Finish `local-codebase` source spec (tree-sitter, libgit2 integration). Finish `webhooks` source spec (local HTTP receiver → JSONL → Coral). Finish `kraken-graph` source spec (KuzuDB embedded).

**Exit criterion:** `coral source test` passes for all 5 custom specs.

**Decision threshold:** If `kraken-graph` doesn't reach passing tests → drop it; ship 4 custom specs not 5; lose $100 + $50 charity but save half a day.

**THE DEMO PATH IS FROZEN AT THE END OF THIS PHASE.** No more changes to V6 or the Reef Map hero rendering. Polish only.

### Phase 2.5 — Reef Memory + learning loop

Implement Reef Memory via LanceDB. Record every successful voyage with its embedding. Retrieve top-3 similar past voyages on every new query. Inject as few-shot exemplars in Quartermaster's prompt.

**Exit criterion:** Second run of V6 measurably faster than first.

**Decision threshold:** If LanceDB integration is fighting CrewAI → skip the learning loop; ship as a "roadmap" feature in the README.

### Phase 2.6 — Bench-O-Bot + observability

Wire Bench-O-Bot to run V6 via direct provider MCPs (GitHub MCP, Sentry MCP, Stripe MCP). Measure and record: latency, token count, cost, accuracy. Build the comparison rendering in Spyglass. Polish all OTel traces so they look clean in Langfuse. Wire PostHog self-referential closure (`coral sql "SELECT * FROM posthog.events"`). Test the morning briefing job via Trigger.dev.

**Exit criterion:** Bench-O-Bot produces consistent, reproducible numbers. Langfuse trace view is screenshot-worthy.

**Decision threshold:** If direct-MCP comparison shows Coral worse on some metric → frame honestly ("Coral is X% better on Y but Z% worse on W; we believe this is because..."). Honesty wins more points than overclaiming.

---

## Macro-phase 3: Submission

The goal of Submission is to package the work for judging. No new functionality lands in this phase. Only recording, writing, and packaging.

### Phase 3.1 — Demo recording

Storyboard the demo video. Record at least 3 takes on a freshly-provisioned environment. Edit in Kdenlive, DaVinci Resolve, or equivalent.

**Exit criterion:** Demo video edited and uploaded; URL ready for README.

**Decision threshold:** If any take has flakiness → re-record from scratch with a fresh environment. Bad demos lose hackathons.

### Phase 3.2 — Blog post

Write the 2-3 page reproducible blog post that qualifies for the Keychron prize. Walk through building KRAKEN with reproducible code snippets. Cover all 5 custom source specs. Demonstrate the cross-source JOIN pattern with at least one full voyage.

**Exit criterion:** Blog post published; URL ready for submission package.

### Phase 3.3 — Discord + social showcase

Post in the Coral Discord `#how-i-coral` channel with screenshots, architectural thesis, and demo link. Cross-post to LinkedIn and X tagging @withcoral.

**Exit criterion:** Discord post live, LinkedIn post live, X post live.

### Phase 3.4 — Upstream source spec PRs

Submit upstream PRs to `withcoral/coral` for every passing custom source spec.

**Exit criterion:** Up to 5 PRs open at `github.com/withcoral/coral/pulls`.

### Phase 3.5 — Final polish + entry submission

Final pass on documentation (ARCHITECTURE.md, PROPOSAL.md, README.md, REQUIREMENTS.md). Run `make test` on a fresh laptop one more time. Verify `docker compose up` works on fresh Mac, Linux, Windows (WSL). Submit hackathon entry via WeMakeDevs Discord / Devpost.

**Exit criterion:** Hackathon submission confirmed.

---

## Cut list (in priority order if behind)

When scope must shrink, cut from the bottom of this list first. Items lower on the list are less central to the pitch.

1. **F30 stretch goals** (voice, Slack bot, embeddable widget, real-time collab) — drop entirely
2. **F18 auto-generated SDK clients** — drop; mention as "coming soon" in README
3. **F11 OpenAPI auto-generation for Source Spec Forge** — drop GraphQL and curl paths; keep OpenAPI only
4. **F17 voyage docs auto-generation** — write docs by hand for the 8 voyages
5. **F22 DBOS durable execution** — fall back to in-memory state; mention as "production roadmap"
6. **F21 Trigger.dev morning briefing** — drop scheduled execution; show as manual `kraken voyage:run risk-heatmap`
7. **`kraken-graph` source spec** — drop; ship 4 custom specs not 5
8. **F13 Voyage Studio** — fall back to read-only viewer with manual YAML editing
9. **Reef Memory learning loop** — drop the embedding pipeline; ship just the SQL blackboard
10. **`webhooks` source spec** — drop; ship 3 custom specs not 4
11. **Bosun (sprint agent)** — fold into Quartermaster; sprint voyage runs but as single-agent
12. **`local-codebase` source spec** — drop; Cooper falls back to GitHub source only

**Hard floor:** even at maximum cuts, the demo still fires because V6 (Executive Escalation) + V1 (Hot Deploy) + V5 (Fresh CVE) all stand alone with bundled + osv + gmail sources.

---

## Decision thresholds with concrete actions

### If Phase 2.1 doesn't complete end-to-end on first attempt
**Action:** Cut V6 down to fewer sources. Drop the Gmail source from V6's SQL and use a fixture file. Hero demo becomes "intercom + stripe + sentry + github + osv" instead of 7 sources.

### If Phase 2.2 finishes with fewer than 4 voyages working
**Action:** Drop Bosun and Lookout (V3 + V5). Reframe submission as "3 voyages unified" not "5 voyages unified". Still wins on cross-source JOIN narrative.

### If Phase 2.3 finishes with a tangled-looking Reef Map
**Action:** Switch to Mermaid for non-hero voyages. Keep React Flow only for the V6 hero with hand-tuned positions. Mermaid is uglier but reliable.

### If Phase 2.4 finishes with fewer than 3 custom source specs validated
**Action:** Stop building new specs. Polish the working ones to merge quality. Submit upstream PRs for the working specs only.

### If Phase 2.6 can't wire the Bench-O-Bot direct-MCP comparison
**Action:** Hardcode the comparison numbers from Coral's published benchmarks. Frame the panel as "Coral's published benchmarks on Claude Opus 4.6" rather than "live reproduction". Less compelling but still factual.

### If Phase 3.1 takes have any flakiness
**Action:** Re-record on a freshly-provisioned laptop. Bad demos lose hackathons.

### If Phase 3.5 reveals anything broken
**Action:** Skip the broken feature in the README. Submit what works. Honest README beats broken demo.

---

## Daily standup template

Each working session starts with a 15-minute standup:

1. **What works** — list every working feature, no exceptions
2. **What's broken** — be ruthlessly honest
3. **What's the biggest risk for today** — name one thing
4. **What's the cut decision if today goes sideways** — name it explicitly before starting

End with: "Demo path status: green/yellow/red." Green = ship-ready. Yellow = working but rough. Red = broken; fix today or cut.

---

## Effort allocation per macro-phase

Macro-phases differ in effort balance. Allocation guidance per phase:

| Macro-phase | Building | Testing | Polish | Documentation |
|---|---|---|---|---|
| 1. Foundation | 70% | 15% | 5% | 10% |
| 2. Build | 60% | 20% | 10% | 10% |
| 3. Submission | 5% | 15% | 25% | 55% |

Building stops at the end of Phase 2.6. After that, only polish and documentation.

---

## Vibecoding rules

Since most of this will be vibecoded by AI agents:

1. **One feature per branch, one PR per feature.** No mega-PRs.
2. **Test before merge.** `make test` must pass. Snapshot tests for voyages.
3. **Update CLAUDE.md when you discover a constraint.** Future-you will thank you.
4. **Read AGENTS.md before modifying agent code.** Read voyage YAML before modifying SQL.
5. **Never modify the demo path once it's frozen.** No exceptions.
6. **Never introduce a new dependency without documenting why** in the PR description.
7. **Commit message format:** `[component] action — brief description`. Example: `[voyage] add V6 exec-escalation — joins gmail through osv`.
8. **Branch naming:** `<phase-id>-<feature-name>`. Example: `phase-2-1-hero-voyage`.
9. **Squash on merge.** Keep main history clean.
10. **Push to a `submission` branch when ready for the judges.** That's what they'll see.

---

## What the coding agent should know

Your AI coding agent (Claude Code, Cursor, etc.) should:

1. **Read CLAUDE.md first** every time it opens the project.
2. **Read ARCHITECTURE.md second** to understand layer boundaries.
3. **Read AGENTS.md** before touching anything in `agents/`.
4. **Read REQUIREMENTS.md** for the spec when implementing a feature.
5. **Read DESIGN.md** when working in `ui/`.
6. **Read this PLAN.md** when deciding what to build next.
7. **Read PROPOSAL.md** to internalize the pitch and not drift from it.
8. **Never ignore the "Forbidden patterns" section in CLAUDE.md.**

---

## Demo rehearsal protocol

Before recording the final demo, run the full demo at least 5 times. Each rehearsal:

1. Time it. Must land within target duration window.
2. Run on a freshly-rebooted laptop with cold cache.
3. Disconnect Wi-Fi at the "Gmail email arrives" moment to prove local-first.
4. Record each take.
5. Watch the recordings as a team. Note any awkwardness.

If any rehearsal exceeds the target by >15% or is visually unclear → cut content from the demo, not from the time budget.

---

## Submission checklist

Before submitting:

- [ ] GitHub repo public with Apache 2.0 license
- [ ] README with installation steps that work on a fresh laptop
- [ ] Demo video uploaded to YouTube/Loom
- [ ] Demo video URL in the README
- [ ] Architecture diagram in README
- [ ] All custom source spec upstream PRs open at `withcoral/coral`
- [ ] Discord showcase posted at `#how-i-coral`
- [ ] LinkedIn post live, tagging @withcoral
- [ ] X post live, tagging @withcoral
- [ ] 2-3 page reproducible blog post published
- [ ] Hackathon entry submitted via WeMakeDevs / Devpost
- [ ] Team registered, all members listed
- [ ] All vibecoding docs in repo: ARCHITECTURE.md, PRD.md, PROPOSAL.md, REQUIREMENTS.md, AGENTS.md, DESIGN.md, SKILL.md, CLAUDE.md, PLAN.md
- [ ] `make test` passing on main
- [ ] `docker compose up` works in <60s

---

## Post-hackathon plan (if we win)

1. Open-source maintenance: respond to issues, accept community PRs
2. Voyage marketplace: ship the `voyages/` PR review process publicly
3. Upstream more source specs to `withcoral/coral`
4. Talk submissions to relevant conferences (NeurIPS, MLSys, AI Engineer Summit)
5. Blog series on the architectural patterns (SQL blackboard, JOIN-as-agent-primitive)

---

> Set the course. Trust the crew. Phases close when their exit criteria are met — not before, not after.
