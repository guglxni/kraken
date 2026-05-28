# Purser — MRR Weighting Skill

## How to prioritize by revenue impact

### Priority score formula

```
priority_score = mrr × (1 + error_rate_multiplier) × urgency_factor
```

Where:
- `error_rate_multiplier = ln(1 + active_errors / 100)` — logarithmic so 1000 errors
  doesn't 10× the score over 100 errors
- `urgency_factor = 3.0 if exec_email_in_inbox else 1.5 if conversation_open else 1.0`

### Tier boundaries (default thresholds)

| Tier | MRR range | Response SLA |
|---|---|---|
| 1 | > $50K/mo | Immediate — escalate now |
| 2 | $10K–$50K | Same day |
| 3 | $5K–$10K | Next business day |
| 4 | < $5K | Standard support queue |

### SQL pattern for priority scoring

```sql
SELECT
  c.email,
  sub.mrr,
  COUNT(DISTINCT s.id)                            AS active_errors,
  sub.mrr
    * (1 + LN(1 + COUNT(DISTINCT s.id)::float / 100))
    * CASE
        WHEN gm.internal_date IS NOT NULL THEN 3.0
        WHEN ic.state = 'open'           THEN 1.5
        ELSE                                  1.0
      END                                         AS priority_score
FROM intercom.contacts c
JOIN stripe.subscriptions sub ON sub.customer_email = c.email
LEFT JOIN sentry.issues s     ON s.tags->>'org' = sub.metadata->>'org_id'
LEFT JOIN intercom.conversations ic ON ic.contact_id = c.id AND ic.state = 'open'
LEFT JOIN gmail.messages gm   ON gm."from" = c.email
                              AND gm.internal_date > NOW() - INTERVAL '24 hours'
WHERE sub.mrr > {{ mrr_threshold }}
GROUP BY c.email, sub.mrr, gm.internal_date, ic.state
ORDER BY priority_score DESC;
```

### Always report the raw MRR

Never abstract MRR into vague tiers in the final finding. Always report:
"Acme Corp ($240,000/mo)" not "a high-value customer".
