# Helm — Deploy Correlation Skill

## How to correlate an incident with a deploy

### Window rule
A deploy is "suspect" if it occurred between 30 minutes before the incident fired
and the incident firing time. Beyond 30 minutes, label correlation "medium" or "low".

### SQL pattern
```sql
SELECT d.sha, d.created_at,
       i.created_at - d.created_at AS lag_to_incident
FROM github.deployments d
JOIN pagerduty.incidents i
  ON d.created_at BETWEEN i.created_at - INTERVAL '30 min'
                      AND i.created_at
WHERE i.id = '{{ incident_id }}'
  AND d.environment = 'production'
ORDER BY lag_to_incident ASC
LIMIT 1;
```

### Confidence reduction rules
- Third-party status page shows degraded/down at incident time → reduce to "medium"
- Multiple deploys in the 30-minute window → reduce to "medium" (ambiguous)
- Previous identical incident (from kraken.findings) resolved without a deploy → reduce to "low"
- Feature flag change in LaunchDarkly at incident time → add as alternative hypothesis

### Evidence to always include
1. The deploy SHA and exact timestamp
2. The lag between deploy and incident (seconds)
3. The PR title and author
4. The files changed (first 5)
