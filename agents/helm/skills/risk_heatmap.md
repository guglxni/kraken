# Helm — Risk Heatmap (V7) Playbook

## Purpose
The Risk Heatmap is the morning briefing voyage. It aggregates risk signals from
every available source into a single ranked list, ordered by weight (severity ×
exposure × recency).

## Execution steps

1. **Run the risk_heatmap voyage.** Parameters: `hours_back=24`, `top_n=50`.

2. **Group by risk kind.** The voyage returns rows with `kind`, `ref`, `weight`.
   Group into: `deploy`, `incident`, `cve`, `whale`, `stale_pr`, `sprint_slip`.

3. **Rank within each group.** Weight is already normalized in the SQL. Present
   top 3 items per group maximum.

4. **Flag any critical items.** Items with weight > threshold by kind:
   - `incident`: any triggered PagerDuty incident
   - `cve`: severity_score >= 9.0
   - `whale`: MRR > 50000 with `past_due` status
   - `deploy`: > 10 associated errors in Sentry

5. **Write finding.** One finding per risk kind with top items.

## Slack post format (for Trigger.dev morning cron)

```
📊 KRAKEN Morning Briefing — {date}

🔴 INCIDENTS ({count}): {list of titles}
⚠️  CVEs ({count}): {list with CVSS scores}
💰 WHALE RISK ({count}): {customer list with MRR}
🚀 HOT DEPLOYS ({count}): {sha list}
🐢 STALE PRs ({count}): oldest is {days} days
📉 SPRINT SLIPS ({count}): {issue list}

Run `kraken voyage:run risk-heatmap` for full details.
```
