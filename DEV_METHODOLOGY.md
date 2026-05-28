# Development Methodology — KRAKEN

> Patterns extracted from `awslabs/aidlc-workflows` (2.5k stars, MIT-0) and
> `shanraisshan/claude-code-best-practice` (55.3k stars). Applied to KRAKEN build.

---

## From `awslabs/aidlc-workflows`

### 1. Adaptive Depth — Skip Phases We've Already Done

AIDLC is a state machine: Inception → Construction → Operations. KRAKEN already has a
complete Inception phase (all 9 planning docs). Jump straight to Construction.

**Rule:** Evaluate complexity first. For KRAKEN's 3-day window, use "minimal" depth for
non-demo features, "comprehensive" depth only for the hero V6 voyage path.

---

### 2. Plan-then-Execute with Explicit Approval Gates

Before any code generation unit:
1. Write a `findings/plan_{voyage_id}.parquet` entry with execution steps
2. Require approval signal (CLI confirmation or Supabase Realtime event)
3. Execute steps sequentially with per-step completion records
4. Verify no duplicate files were created (brownfield rule: modify, don't duplicate)

**For KRAKEN:** Quartermaster writes `kraken.plans` row → Specialist reads it → executes
step-by-step → writes `kraken.findings` → Quartermaster synthesizes. Already the
architecture. Formalize it as a checklist in voyage YAML `steps:` field.

---

### 3. Rules-as-Files with Lazy Loading

Never load all rules into every agent context. Each agent loads only what the current
phase needs.

**Applied to KRAKEN file structure:**

```
agents/
  quartermaster/
    SOUL.md          ← always loaded (persona)
    RULES.md         ← always loaded (hard constraints)
    skills/
      routing.md     ← lazy: loaded when routing a question
      synthesis.md   ← lazy: loaded when synthesizing findings
  helm/
    SOUL.md
    RULES.md
    skills/
      incident_summary.md   ← lazy: loaded when running V2
      risk_heatmap.md       ← lazy: loaded when running V7
kraken/
  voyages/
    CLAUDE.md        ← lazy: loads only when editing voyage YAML files
ui/
  CLAUDE.md          ← lazy: loads only when editing UI files
```

Root `CLAUDE.md` stays under 200 lines (hard rules + forbidden patterns only).

---

### 4. UI Test IDs as a Code Generation Rule

Every frontend interactive element gets `data-testid="{component}-{element-role}"` baked
in at generation time, not retrofitted.

**Examples for KRAKEN UI:**
- `data-testid="reef-map-node-github"`
- `data-testid="spyglass-input"`
- `data-testid="bench-o-bot-coral-latency"`
- `data-testid="anchor-approve-btn"`
- `data-testid="voyage-card-exec-escalation"`

Add to `ui/CLAUDE.md` as a TypeScript convention.

---

### 5. Multi-Agent Design Review with Severity Scoring

AIDLC's design review: Critique agent (blocking) → Alternatives + Gap Analysis agents
(parallel). Findings scored: CRITICAL×4, HIGH×3, MEDIUM×2, LOW×1.

**Applied to KRAKEN's Bench-O-Bot:**
- Critique agent evaluates the direct-MCP path findings
- Alternatives agent evaluates the Coral path (with critique as context)
- Weighted scores stored in `kraken.findings` for the UI comparison panel
- This turns Bench-O-Bot from a latency stopwatch into a semantic quality comparison

---

### 6. CI Security Stack (add `make security-check`)

```
.pre-commit-config.yaml    → markdownlint + trailing whitespace
bandit                     → Python security scanning on kraken/
semgrep                    → custom rules for Coral SQL injection patterns
gitleaks                   → secret detection (with .gitleaks-baseline.json)
checkov                    → IaC security on infra/docker-compose.yaml
```

Add `make security-check` target, wire into CI alongside `make test`.

---

### 7. Overconfidence Prevention as RULES.md Rule

Add to every agent's `RULES.md`:
- Flag any voyage parameter that uses range language without a concrete bound
- Block execution if clarification questions are unresolved
- Never assume a missing parameter has a default — ask
- Questions go into `kraken.findings` kind=`clarification`, not the chat turn

---

### 8. AI Evaluator Pattern for CI (voyage snapshot tests)

```
Execute → Post-Run → Quantitative → Contract → Qualitative → Report
```

- **Quantitative gate:** ruff + bandit (Python), Biome (TypeScript)
- **Contract gate:** Pydantic model validation on all voyage output schemas
- **Qualitative gate:** Claude Haiku scores voyage output semantic alignment vs. golden baseline
- **Docker sandbox:** Voyage agents run in containers during CI — no production credentials
- **Report artifact:** Attached to every PR as a CI artifact

---

## From `shanraisshan/claude-code-best-practice`

### 1. Command → Agent → Skill Composition

The canonical architecture:
```
Command (entry point, orchestrates via AskUserQuestion + Agent + Skill only)
  └─ Agent (specialist, narrow tool allowlist, fail-closed on wrong output format)
       └─ Skill (atomic capability, single tool allowlist, context:fork for isolation)
```

**Map to KRAKEN:**
- Voyage YAML = Command
- `agents/{name}/` = Agent
- `skills/voyage-*.md` = Skills

**Critical rule: the orchestrator is forbidden from doing the work itself.**
Quartermaster's allowed_tools = `[coral_sql, write_plan, reef_memory_recall]` only.

---

### 2. 16-Field Agent Frontmatter (standardize `agent.yaml`)

Full schema for every `agents/{name}/agent.yaml`:

```yaml
name: agent-name
description: "Trigger description for auto-invocation"
tools: [coral_sql, composio_draft_email]
disallowedTools: [Bash, Write]
model: sonnet            # haiku/sonnet/opus
effort: high             # Opus 4.6 only
maxTurns: 10
isolation: worktree      # for Cooper (runs code)
permissionMode: plan     # for Lookout (read-only)
skills: [primary_voyage]
mcpServers: [coral-mcp]
memory: project
background: false
color: green
```

Per-agent model assignments:
- Quartermaster: `model: opus` (routing needs deep reasoning)
- Helm: `model: opus, effort: high` (incident diagnosis)
- Cooper: `model: sonnet, isolation: worktree` (code execution sandbox)
- Bosun: `model: haiku, maxTurns: 5` (sprint summaries don't need deep reasoning)
- Purser: `model: opus` (CEO communication quality matters)
- Lookout: `model: sonnet, permissionMode: plan` (read-only, never writes)

---

### 3. CLAUDE.md Size Discipline

**Current problem:** Root `CLAUDE.md` is 12,044 bytes — too long for reliable attention.

**Refactor plan:**
- Root `CLAUDE.md`: 6 hard rules + forbidden patterns only (~60 lines)
- `agents/quartermaster/CLAUDE.md`: Routing logic, voyage dispatch rules
- `kraken/voyages/CLAUDE.md`: SQL convention rules (lazy-load when editing voyages)
- `ui/CLAUDE.md`: TypeScript/React conventions (lazy-load when editing UI)
- `sources/CLAUDE.md`: Rust YAML manifest conventions

Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "80"` in `.claude/settings.json`.

---

### 4. `.claude/settings.json` for KRAKEN

```json
{
  "defaultMode": "plan",
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80"
  },
  "permissions": {
    "deny": [
      "Bash(rm -rf*)",
      "Bash(git push --force*)",
      "Write(.env*)",
      "Write(infra/*)"
    ]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "type": "command",
      "command": "python3 .claude/hooks/audit_tool_use.py",
      "async": true,
      "timeout": 5000
    }],
    "Stop": [{
      "type": "command",
      "command": "python3 .claude/hooks/write_voyage_completion.py"
    }],
    "SessionStart": [{
      "type": "command",
      "command": "python3 .claude/hooks/load_voyage_state.py",
      "timeout": 3000
    }]
  }
}
```

---

### 5. Context Management Rules (add to CLAUDE.md)

- Spawn a subagent for any exploration task (20+ file reads, dead ends). Only the
  result returns to parent context — the noise is GC'd.
- Target subtask completion under 50k tokens. If a voyage requires more, decompose.
- Use `/rewind` over corrections when an agent goes down a wrong path. Don't accumulate
  failed attempts.
- Compact at ~50% context with a hint, not default auto-compact.

---

### 6. Parallel Worktree Execution for Multi-Agent Voyages

When Quartermaster dispatches parallel voyages (Helm + Cooper + Bosun all triggered by
one incident), each specialist runs in its own git worktree:
- Agents write findings to `kraken.findings` Parquet (the shared blackboard)
- No direct agent-to-agent calls (already Rule 5)
- Worktrees clean up after voyage completes
- Quartermaster JOINs all findings via Coral for final synthesis

This is the aidlc `ThreadPoolExecutor` pattern applied to KRAKEN's CrewAI Flows.

---

### 7. Tool Allowlist as Architectural Enforcement

The Quartermaster's tool allowlist is not just security — it is the mechanical
enforcement of Rule 1 (Coral-only reads). If the allowlist permits `import github`,
it will eventually be used.

**Tool allowlists by agent:**
- Quartermaster: `coral_sql` (schema/findings only), `write_plan`, `reef_memory_recall`
- Helm: `coral_sql` (SRE sources only)
- Cooper: `coral_sql` (code sources only)
- Bosun: `coral_sql` (sprint sources only)
- Purser: `coral_sql` (customer sources only), `composio_draft_email`, `composio_create_intercom_note`
- Lookout: `coral_sql` (security sources only)

---

### 8. Fail-Closed on Output Format Mismatch

If the expected Pydantic output schema isn't returned by an agent, stop and report
failure. Never improvise a workaround. This applies to:
- Coral SQL responses (structured exception with query text logged)
- Agent-to-agent handoffs (Pydantic validation on all `Finding` and `Plan` models)
- Voyage output schemas (validated against declared contract in voyage YAML)

Already in CLAUDE.md (`No Any types`). Reinforce: validation failure = voyage failure,
not retry with relaxed schema.

---

## Combined Priority Rules for the 3-Day Build

1. **Vertical slice first.** Get V6 (exec_escalation) end-to-end before adding breadth.
   This means: Purser agent → Coral SQL → V6 voyage → Reef Map renders → done.
   Then add Quartermaster routing, then V1, then V5.

2. **Subagent for context protection.** Use Claude Code subagents for source spec
   writing, UI component building, and test writing. Only final results return to main
   context.

3. **Brownfield rule.** Before generating any file, check if it exists. Modify, don't
   duplicate. Especially important for voyage YAML — one canonical file per voyage.

4. **Test before merge.** `make test` must pass before any feature is considered done.
   Snapshot test per voyage. Prompt test per agent.

5. **Demo path is frozen after Day 2.** Once V6 runs end-to-end, no changes to:
   - `kraken/voyages/exec_escalation.yaml`
   - `agents/purser/`
   - `agents/quartermaster/` routing for exec-escalation
   - Reef Map node positions for the V6 hero flow

6. **Cut list is pre-decided.** In order of cutting if behind:
   - Voyage Studio drag-and-drop → static read-only viewer
   - DBOS durable execution → in-memory state
   - Reef Memory learning loop → stub
   - `kraken-graph` source spec → drop to 3 custom specs
   - Bosun agent → fold into Quartermaster
   - `webhooks` source spec → drop to 2 custom specs (OSV + local-codebase)
