# Helm — Metric Anomaly Detection Skill

## When a metric change is statistically meaningful

### Thresholds by metric type

| Metric | Anomaly threshold | Note |
|---|---|---|
| p99 latency | > 2× baseline (1h window) | Use LAG() window function |
| error rate | > 3× baseline | Compare to same hour prior 7 days |
| p50 latency | > 1.5× baseline | More sensitive; lower threshold |
| success rate | < 95% | Absolute threshold |
| throughput | > 30% drop | Sudden drops indicate upstream block |

### SQL pattern (using window functions)
```sql
SELECT
  m.timestamp,
  m.value                                                    AS current_value,
  LAG(m.value) OVER (ORDER BY m.timestamp)                  AS prior_value,
  m.value / NULLIF(LAG(m.value) OVER (ORDER BY m.timestamp), 0) AS ratio
FROM datadog.metrics m
WHERE m.metric_name = 'p99_latency'
  AND m.tags->>'org' = '{{ org_id }}'
  AND m.timestamp > NOW() - INTERVAL '2 hours'
ORDER BY m.timestamp DESC;
```

### Reporting format
Always state: "p99 went from Xms to Yms (Z× increase) between [time1] and [time2]".
Never say "latency increased significantly" without numbers.
