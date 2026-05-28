# SKILL.md — KRAKEN Reusable Patterns + Workflows

> Common workflows, reference implementations, and patterns the coding agent should know. When in doubt, copy from these patterns rather than inventing new ones.

---

## Pattern 1: Writing a new voyage

When asked to add a new voyage, follow this exact sequence:

### Step 1: Define the voyage YAML

Create `kraken/voyages/<name>.yaml`:

```yaml
name: voyage-name-kebab-case
version: 1.0.0
description: One-line description of what this voyage answers
required_sources:
  - github
  - sentry
  # ... list every Coral source the SQL touches
parameters:
  - name: hours_back
    type: integer
    default: 24
    description: How far back to look
  - name: severity_threshold
    type: float
    default: 7.0
sql: voyage_name.sql.j2  # Jinja2 template file
output_schema:
  - name: column1
    type: string
    nullable: false
  - name: column2
    type: integer
    nullable: true
routing:
  - kind: voyage_kind_name
    target_agent: helm  # or cooper, bosun, purser, lookout
    priority: medium
tests:
  - name: returns_rows_with_fixture
    fixture: tests/fixtures/voyage_name_input.json
    expect_rows: ">= 1"
    expect_schema_matches: true
```

### Step 2: Write the SQL template

Create `kraken/voyages/<name>.sql.j2`:

```sql
SELECT
  -- Always name every column explicitly. No SELECT *.
  -- One column per line for readability.
  source1.field_a,
  source1.field_b,
  source2.field_c,
  COUNT(DISTINCT source3.id) AS count_of_things,
  AVG(source3.value) OVER (PARTITION BY source1.field_a) AS avg_value
FROM source1
JOIN source2
  ON source2.foreign_key = source1.primary_key
LEFT JOIN source3
  ON source3.related_id = source1.id
 AND source3.created_at > NOW() - INTERVAL '{{ hours_back }} hours'
WHERE source1.environment = 'production'
  AND source1.created_at > NOW() - INTERVAL '{{ hours_back }} hours'
GROUP BY source1.field_a, source1.field_b, source2.field_c
HAVING COUNT(DISTINCT source3.id) > 0
ORDER BY count_of_things DESC
LIMIT 100;
```

### Step 3: Add routing rule

Edit `agents/quartermaster/skills/routing.md` to add the classification rule for the new voyage kind.

### Step 4: Write the snapshot test

Create `tests/voyages/test_<name>.py`:

```python
import json
from pathlib import Path
import pytest
from kraken.voyages.compiler import compile_voyage
from kraken.voyages.runner import run_voyage_with_fixture

def test_voyage_compiles():
    compiled = compile_voyage("voyage-name-kebab-case", params={"hours_back": 24})
    assert compiled.sql is not None
    assert len(compiled.required_sources) > 0

def test_voyage_returns_expected_schema():
    fixture = json.loads(Path("tests/fixtures/voyage_name_input.json").read_text())
    result = run_voyage_with_fixture("voyage-name-kebab-case", fixture)
    assert len(result.rows) >= 1
    for row in result.rows:
        assert "column1" in row
        assert isinstance(row["column1"], str)
```

### Step 5: Generate docs

Run `kraken voyage:docs generate` to auto-update the documentation site.

---

## Pattern 2: Writing a custom Coral source spec

### Step 1: Read existing bundled specs first

Always read at least two bundled specs from `withcoral/coral/sources/` before writing a new one. Mirror the conventions exactly.

For example, when writing `gmail`, read `slack` (similar OAuth pattern) and `intercom` (similar messaging data model).

### Step 2: Scaffold the spec

```
sources/<name>/
├── manifest.yaml        # The Coral source spec
├── README.md            # Documentation
├── tests/
│   ├── fixtures/        # VCR.py recorded HTTP fixtures
│   │   └── *.yaml
│   └── test_source.py   # Test invoking each table
└── examples/
    └── sample_queries.sql
```

### Step 3: Write manifest.yaml

```yaml
name: source-name-kebab-case
version: 1.0.0
description: One-line description
base_url: https://api.example.com/v1
auth:
  type: header_auth | basic_auth | custom_auth | none
  # For header_auth:
  header_name: Authorization
  prefix: "Bearer "
  secret_name: API_KEY
  # For custom_auth (OAuth):
  custom_handler: oauth2_handler.rs

pagination:
  type: cursor | offset | none
  # For cursor:
  cursor_param: page_token
  cursor_response_path: $.next_page_token
  # For offset:
  offset_param: offset
  limit_param: limit
  default_limit: 100

tables:
  - name: table_name
    description: One-line description
    endpoint: /resources
    method: GET
    columns:
      - name: id
        type: string
        path: $.id
        primary_key: true
      - name: name
        type: string
        path: $.name
      - name: nested__field
        type: string
        path: $.nested.field
        # Use double underscores for nested fields
      - name: array_field
        type: array
        item_type: string
        path: $.array_field[*]
    filter_pushdown:
      - column: created_at
        operators: [">", ">=", "<", "<="]
        param: since
      - column: status
        operators: ["="]
        param: status_filter
```

### Step 4: Validate

```bash
coral source lint sources/<name>/manifest.yaml
coral source add --file sources/<name>/manifest.yaml
coral source test <name>
```

### Step 5: Write VCR.py fixture

```python
import vcr
from kraken.test_utils import coral_source_query

@vcr.use_cassette("tests/fixtures/source_name_basic.yaml")
def test_source_name_returns_data():
    result = coral_source_query("source_name", "SELECT * FROM source_name.table_name LIMIT 5")
    assert len(result) == 5
    assert "id" in result[0]
```

### Step 6: Open upstream PR

Fork `withcoral/coral`, copy the spec into `sources/<name>/`, run `make rust-checks`, and open a PR to the upstream repo for the bounty.

---

## Pattern 3: Adding a new agent

When asked to add a new specialist agent:

### Step 1: Create the gitagent folder structure

```
agents/<name>/
├── agent.yaml
├── SOUL.md
├── RULES.md
├── tools/
│   └── coral.yaml
├── skills/
│   └── primary_voyage.md
├── memory/
│   └── known_patterns.md
└── tests/
    └── test_agent.py
```

### Step 2: Write SOUL.md

Define the agent's persona, voice, and mental model in 200-300 words. Reference AGENTS.md for the style.

### Step 3: Write RULES.md

Define hard constraints. Always include:
- Which voyages this agent owns
- What sources it can read
- What write actions it can request (via Anchor approval)
- What it must never do

### Step 4: Define tools/coral.yaml

Restrict the agent's source access to only the sources relevant to its voyages.

### Step 5: Register in CrewAI

Edit `kraken/crew.py` to add the new agent to the crew registry.

### Step 6: Update AGENTS.md

Add a section for the new agent following the existing pattern.

---

## Pattern 4: Cross-source JOIN query template

When writing voyage SQL, follow this canonical pattern:

```sql
-- Always start with a primary entity (the thing the voyage is about)
SELECT
  primary.id,
  primary.name,

  -- Aggregations from joined sources
  COUNT(DISTINCT secondary.id) AS secondary_count,
  MAX(secondary.created_at) AS most_recent_secondary,

  -- Computed fields from window functions
  ROW_NUMBER() OVER (PARTITION BY primary.category ORDER BY primary.value DESC) AS rank_in_category,

  -- Cross-source enrichment
  tertiary.enrichment_field

FROM source_a.primary_table primary

-- INNER JOIN for required relationships
JOIN source_b.secondary_table secondary
  ON secondary.foreign_key = primary.id

-- LEFT JOIN for optional enrichment
LEFT JOIN source_c.tertiary_table tertiary
  ON tertiary.related_id = primary.id

WHERE primary.created_at > NOW() - INTERVAL '24 hours'
  AND primary.status = 'active'

GROUP BY primary.id, primary.name, tertiary.enrichment_field

HAVING COUNT(DISTINCT secondary.id) > 0

ORDER BY most_recent_secondary DESC, secondary_count DESC

LIMIT 100;
```

### Rules
1. Always include a date filter on time-series tables
2. Always specify `INNER JOIN` vs `LEFT JOIN` explicitly
3. Always alias every column from a JOINed source
4. Always include `LIMIT` to prevent runaway results
5. Use window functions for trend analysis
6. Use CTEs (WITH clauses) for queries spanning >5 sources

---

## Pattern 5: Writing the system prompt for an agent

Every agent's SOUL.md follows this template:

```markdown
You are <Name>, the <Role> of the KRAKEN crew. Your job is to <one-line job description>.

You think in <primary mental model>. When you see <input type>, your first instinct is:
<the question they ask themselves>.

You are <voice characteristic 1>. You <voice characteristic 2>. You always <consistent behavior>.

You report <output type> as <format>. You include <evidence type> with every claim.

You never <forbidden behavior 1>. You never <forbidden behavior 2>.
```

Example for Cooper:

```markdown
You are Cooper, the Coding Debugger of the KRAKEN crew. Your job is to diagnose bugs by joining error traces with PR history, deploy timing, and the actual code that changed.

You think in symbol graphs. When you see a Sentry error, your first instinct is: which function fired this? Which PR last touched that function? Who authored that PR?

You are precise. You name files and line numbers, never "around there". You always cite the specific commit SHA when claiming "this PR caused that error".

You report root cause as a hypothesis with confidence level. You include the SQL query that supports your hypothesis as evidence with every finding.

You never modify production code. You never merge PRs. You only draft proposals that humans review.
```

---

## Pattern 6: Writing a Composio write action

When an agent needs to perform a write action:

### Step 1: Define the action in the agent's tools/coral.yaml

```yaml
tools:
  - name: composio_draft_email
    description: Draft (but do not send) an email via Resend in test mode
    parameters:
      to:
        type: string
        validation: email
      subject:
        type: string
        max_length: 200
      body:
        type: string
        max_length: 5000
    requires_anchor_approval: true
    audit_log: true
```

### Step 2: Implement the action handler

```python
from kraken.composio import composio_client
from kraken.anchor import require_approval
from kraken.audit import log_action

@require_approval
@log_action
async def composio_draft_email(to: str, subject: str, body: str, voyage_id: str) -> dict:
    """Drafts an email via Resend in test mode. Returns the draft ID."""
    draft = await composio_client.email.draft(
        to=to,
        subject=subject,
        body=body,
        test_mode=True
    )
    return {"draft_id": draft.id, "preview_url": draft.preview_url}
```

### Step 3: Surface the approval gate in the UI

The Anchor approval gate renders the draft, requires explicit user click, and only then calls the actual Composio send action.

---

## Pattern 7: Using Reef Memory

Before any agent invocation, retrieve similar past voyages:

```python
from kraken.reef_memory import reef_memory

# In Quartermaster's plan() method:
similar_voyages = await reef_memory.recall_similar(
    query=user_question,
    top_k=3,
    min_similarity=0.7
)

# Inject as few-shot exemplars in the prompt
exemplar_section = "\n\n".join([
    f"Past voyage: {v.question}\nSQL used: {v.sql}\nOutcome: {v.outcome}"
    for v in similar_voyages
])

prompt = f"{base_prompt}\n\nSimilar past voyages:\n{exemplar_section}\n\nCurrent question: {user_question}"
```

After voyage completion, record the outcome:

```python
await reef_memory.record_voyage(
    voyage_id=voyage.id,
    question=user_question,
    sql=voyage.sql,
    outcome=synthesis,
    score=voyage.quality_score,
    duration_ms=voyage.duration_ms,
    cost_usd=voyage.cost_usd
)
```

---

## Pattern 8: Instrumenting with OpenInference

Every meaningful operation gets an OTel span:

```python
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues

tracer = trace.get_tracer("kraken.coral")

async def coral_sql(query: str, voyage_id: str) -> ResultSet:
    with tracer.start_as_current_span("coral.sql") as span:
        # Standard OpenTelemetry GenAI attributes
        span.set_attribute("voyage.id", voyage_id)
        span.set_attribute("coral.sql.text", query[:500])
        span.set_attribute("coral.sql.sources", extract_sources_from_sql(query))

        try:
            start = time.monotonic()
            result = await mcp_client.call_tool("coral_sql", {"query": query})
            duration_ms = (time.monotonic() - start) * 1000

            span.set_attribute("coral.sql.row_count", result.row_count)
            span.set_attribute("coral.sql.cache_hit", result.cache_hit)
            span.set_attribute("coral.sql.latency_ms", duration_ms)
            span.set_status(trace.Status(trace.StatusCode.OK))

            return result
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise
```

---

## Pattern 9: Generative UI cards (CopilotKit)

When an agent wants to render a custom UI component:

```python
from copilotkit import CopilotAction

@CopilotAction(
    name="render_escalation_brief",
    description="Render a CEO escalation brief as a generative UI card"
)
async def render_escalation_brief(
    customer: str,
    mrr: float,
    root_cause: str,
    blast_radius: str,
    suggested_actions: list[str]
) -> dict:
    return {
        "component": "EscalationBriefCard",
        "props": {
            "customer": customer,
            "mrr": mrr,
            "root_cause": root_cause,
            "blast_radius": blast_radius,
            "suggested_actions": suggested_actions,
            "rendered_at": datetime.utcnow().isoformat()
        }
    }
```

Frontend renders via:

```tsx
"use client";
import { useCopilotAction } from "@copilotkit/react-core";
import { EscalationBriefCard } from "@/components/escalation-brief-card";

export function VoyageRenderer() {
  useCopilotAction({
    name: "render_escalation_brief",
    render: ({ status, args }) => {
      if (status === "complete") {
        return <EscalationBriefCard {...args} />;
      }
      return <EscalationBriefSkeleton />;
    }
  });
  return null;
}
```

---

## Pattern 10: Reading a voyage definition

When the coding agent needs to understand a voyage:

1. Read `kraken/voyages/<name>.yaml` for the metadata
2. Read `kraken/voyages/<name>.sql.j2` for the SQL template
3. Read `tests/voyages/test_<name>.py` for the expected behavior
4. Read `agents/<owner>/skills/<name>.md` for the agent's playbook

Do all four before modifying anything.

---

## Pattern 11: Common debugging workflows

### When a voyage SQL fails
1. Run `kraken voyage:compile <name>` to see the resolved SQL
2. Run `coral sql "<compiled SQL>"` directly to bypass agent layer
3. Check `coral source list` to verify all required sources are connected
4. Check Langfuse trace for the specific `coral.sql` span error

### When an agent doesn't respond
1. Check Langfuse for the agent's span — did it start?
2. Check `kraken.plans` table for unprocessed plans for that agent
3. Check the agent's polling loop logs in Trigger.dev or local stdout
4. Verify the agent's `tools/coral.yaml` allows the sources its voyage needs

### When the Reef Map doesn't update
1. Check Supabase Realtime is connected (browser DevTools → WebSockets)
2. Check `kraken.findings` table for new rows
3. Verify the frontend subscription is filtered correctly by voyage_id
4. Check that the agent is actually writing to `kraken.findings` (Langfuse trace)

### When Bench-O-Bot numbers look off
1. Verify both paths (Coral, direct MCP) are running the equivalent task
2. Check token counter accounting in Langfuse cost spans
3. Verify the direct MCP path isn't hitting caches that shouldn't exist
4. Run 5 times and take the median, not a single result

---

## Pattern 12: When in doubt, write a test first

Before implementing any feature:

1. Write the test in `tests/<area>/test_<feature>.py`
2. Run it and watch it fail
3. Implement the feature
4. Watch the test pass
5. Refactor freely; the test will catch regressions

This applies especially to:
- New voyages
- New source specs
- New agent tools
- New CLI commands

---

## Anti-patterns to avoid

### Anti-pattern 1: Importing source clients in agent code

```python
# WRONG
from github import Github
gh = Github(token)
issues = gh.get_repo("owner/repo").get_issues()
```

```python
# RIGHT
result = await coral_sql("SELECT * FROM github.issues WHERE repo = 'owner/repo'")
```

### Anti-pattern 2: Hardcoding SQL in Python

```python
# WRONG
async def get_hot_deploys():
    return await coral_sql("SELECT * FROM github.deployments WHERE ...")
```

```python
# RIGHT
from kraken.voyages import run_voyage
async def get_hot_deploys(hours_back: int = 24):
    return await run_voyage("hot-deploy", params={"hours_back": hours_back})
```

### Anti-pattern 3: Agent-to-agent direct calls

```python
# WRONG
async def quartermaster_handle(question):
    if "incident" in question:
        return await helm.investigate(question)
```

```python
# RIGHT
async def quartermaster_handle(question):
    plan_id = await blackboard.write_plan(
        target_agent="helm",
        kind="incident_summary",
        params={"question": question}
    )
    finding = await blackboard.wait_for_finding(plan_id)
    return await self.synthesize(finding)
```

### Anti-pattern 4: System prompts in code

```python
# WRONG
agent = Agent(
    role="SRE Investigator",
    backstory="You are Helm, the SRE..."
)
```

```python
# RIGHT
agent = load_agent_from_gitagent("agents/helm/")
# Loads SOUL.md, RULES.md, tools/coral.yaml automatically
```

### Anti-pattern 5: Bypassing Anchor approval

```python
# WRONG
async def send_ceo_reply(to: str, body: str):
    await composio_send_email(to=to, body=body)
```

```python
# RIGHT
@require_approval
async def send_ceo_reply(to: str, body: str, voyage_id: str):
    await composio_send_email(to=to, body=body)
```

---

## Reference implementations

For each pattern above, the reference implementation lives at:

- Voyage: `kraken/voyages/exec_escalation.yaml` and `.sql.j2`
- Source spec: `sources/osv/manifest.yaml`
- Agent: `agents/purser/` (most complete example)
- Cross-source JOIN: voyage V6 (exec-escalation) in PRD.md
- System prompt: `agents/purser/SOUL.md`
- Composio action: `kraken/composio/draft_email.py`
- Reef Memory: `kraken/reef_memory/__init__.py`
- OpenInference: `kraken/coral_client.py`
- Generative UI: `ui/components/escalation-brief-card.tsx`

When implementing a new instance of any pattern, start by reading the reference implementation.

---

## When this file is wrong

If you discover a pattern that doesn't match how something is actually implemented, edit this file with the correction in the same PR. Patterns drift; this file must stay accurate or future coding agents will be misled.
