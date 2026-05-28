# Helm — Incident Auto-Summary (V2) Playbook

## Execution steps

1. **Identify the incident.** Query `pagerduty.incidents WHERE status = 'triggered'`
   (or by ID if provided). Record `incident_id`, `created_at`, `urgency`.

2. **Find the suspect deploy.** Query `github.deployments` for any deploy within
   the 30-minute window before the incident fired. If multiple deploys, rank by
   recency. Record `sha`, `deploy_time`.

3. **Find the suspect PR.** JOIN `github.pulls ON merge_commit_sha = deploy.sha`.
   Record `pr_title`, `author`, `additions`, `deletions`, `changed_files`.

4. **Check third-party status.** Query `statusgator.statuses WHERE status != 'up'
   AND last_changed > incident.created_at - 1 hour`. If a third-party is down,
   reduce confidence in deploy correlation.

5. **Gather responders.** Query `slack.messages WHERE channel = '#inc-{incident_id}'`.
   Record unique user set and last message timestamp.

6. **Check Reef Memory.** Query `kraken.findings WHERE kind = 'incident_resolution'
   AND payload->>'error_pattern' LIKE '%{incident_title}%' LIMIT 3`. If similar past
   resolutions exist, surface them.

7. **Assess confidence.**
   - `high`: deploy within 30 min AND metric anomaly statistically significant AND
     no third-party outage
   - `medium`: deploy exists but outside 30 min window OR third-party outage present
   - `low`: no matching deploy OR third-party is down

8. **Write finding.** Structured as `IncidentBrief`.

## Output schema (IncidentBrief)

```json
{
  "incident_id": "INC-4821",
  "title": "Dashboard API p99 > 10s",
  "suspect_deploy": "abc123f",
  "suspect_pr": "PR #4521: add bulk export endpoint",
  "author": "ada.lovelace",
  "third_party_outage": null,
  "confidence": "high",
  "evidence": [
    "Deploy abc123f at 14:30 UTC, incident fired 14:47 UTC (17min gap)",
    "p99 latency: 0.8s baseline → 12.4s post-deploy (15× increase)",
    "PR #4521 added N+1 query in DashboardController#index"
  ]
}
```
