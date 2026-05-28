# Quartermaster Synthesis Skill

## How to write the 4-bullet final answer

After all specialist findings are in, synthesize them into exactly 4 bullets.
Each bullet is one sentence of fact followed by one sentence of suggested action.

### Format

```
• [FINDING] [entity] has [quantified state]. → [ACTION verb] [target] via Anchor approval.
• [FINDING] [metric] shows [quantified change] since [event]. → [ACTION verb] [target].
• [FINDING] [root cause hypothesis] with [confidence level] confidence. → [ACTION verb] [target].
• [FINDING] [risk or opportunity] if [condition]. → [ACTION verb] [target].
```

### Rules
1. Every bullet must include a number or timestamp. No vague statements.
2. Every action must name which Composio tool fires when approved.
3. Confidence levels: high / medium / low. Include the level when it is medium or low.
4. If fewer than 4 meaningful findings exist, write fewer bullets. Never pad.
5. Lead with the highest-MRR or highest-severity finding first.

### Example output

```
• Acme Corp ($240K MRR) has 3,400 unresolved Sentry errors since deploy abc123f at 14:30 UTC. → Draft CEO reply via Anchor → composio_draft_email.
• P99 latency for Acme is 12.4s (up from 0.8s baseline) — correlated with PR #4521 "add bulk export endpoint". → Page on-call via Anchor → composio_page_pagerduty.
• CVE-2024-45490 (CVSS 9.1) in package fast-xml-parser@4.3.2 ships in that same deploy (medium confidence — no in-the-wild exploit yet). → Create Linear security ticket via Anchor → composio_create_linear_ticket.
• 2 other enterprise customers (Globex $180K, Initech $95K) show similar error spikes — blast radius is 3 accounts totalling $515K MRR. → Notify CS leads via Anchor → composio_post_slack.
```

### When synthesis is blocked

If a finding has status "failed" or "timeout", report:
```
• [Agent] could not complete [voyage kind] — [error summary]. → Retry the voyage or check Spyglass for the error trace.
```
