# Helm — Known Patterns

## Learned from past incident investigations

_This file is updated when an incident resolution is confirmed correct (quality_score > 0.8)._

---

## Pattern: statusgator degraded + deploy within 30min = "medium" not "high"

When a third-party service shows degraded status at the time of the incident,
always reduce confidence to "medium" even if the deploy timing is perfect.
The third-party degradation is an alternative hypothesis that cannot be ruled out
without more data.

## Pattern: LaunchDarkly flag changes are as suspect as deploys

If a feature flag changed state within 30 minutes of the incident, report it as an
alternative hypothesis alongside any deploy correlation. Flag rollbacks have resolved
multiple past incidents.

## Pattern: risk_heatmap SQL is expensive — always add LIMIT 50

The risk_heatmap CTE touches 6 tables simultaneously. Without LIMIT, it can return
thousands of rows and exceed the 30s voyage SLA. Always LIMIT to top 50.
