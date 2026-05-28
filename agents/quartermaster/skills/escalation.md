# Quartermaster Escalation Skill

## When to route to multiple specialists in parallel

Single-agent dispatch is the default. Multi-agent dispatch is reserved for questions
that genuinely require data from different domains simultaneously.

### Escalation decision tree

```
User question arrives
        │
        ▼
Does question touch BOTH SRE signals AND code-level cause?
        │
       YES → dispatch helm (V2) + cooper (V1) in parallel
        │
       NO  → continue
        │
        ▼
Is question an exec escalation with security exposure?
        │
       YES → dispatch purser (V6) + lookout (V5) in parallel
        │
       NO  → continue
        │
        ▼
Is question the morning briefing (V7)?
        │
       YES → dispatch helm (V7) always
             + purser (V4) if any whale has open tickets
        │
       NO  → dispatch single specialist per routing.md
```

### Priority assignment for parallel dispatches

When dispatching multiple agents:
- Assign `critical` priority to the voyage that gates the CEO reply or rollback decision
- Assign `high` to voyages that provide supporting context
- Assign `medium` to voyages that enrich but don't block the synthesis

### Synthesis wait strategy

1. Start synthesis timer when first finding arrives
2. Wait up to 25 seconds for remaining findings (leave 5s buffer for 30s total voyage SLA)
3. If a specialist has not returned a finding within 25s, synthesize with what is available
4. Mark any missing specialist's contribution as "pending" in the output
5. Set a Trigger.dev follow-up job to complete the synthesis when the finding arrives

### Parallel dispatch example (exec escalation + CVE)

```python
plans = [
    Plan(
        target_agent="purser",
        kind="exec_escalation",
        params={"sender_email": "ceo@acme.com", "mrr_threshold": 10000},
        priority="critical",
    ),
    Plan(
        target_agent="lookout",
        kind="fresh_cve",
        params={"hours_back": 48, "severity_threshold": 7.0},
        priority="high",
    ),
]
# Both plans written to kraken.plans; agents poll independently
```
