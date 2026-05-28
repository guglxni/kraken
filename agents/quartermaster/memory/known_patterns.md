# Quartermaster — Known Patterns

## Learned from past voyages (git-versioned institutional memory)

_This file is updated automatically when a voyage completes with a quality_score > 0.8.
Add manual learnings below the auto-generated section._

---

## Pattern: exec_escalation always requires purser + lookout parallel dispatch

When an executive email arrives from a customer with MRR > $50K, dispatch both
purser (V6) and lookout (V5) in parallel. The CVE context from Lookout materially
improves the quality of Purser's email draft.

## Pattern: morning briefing = risk_heatmap + angry_whales if any past_due

The 08:30 cron should always run V7. If V7 returns any `whale` rows with
`weight > 10000`, also dispatch V4 to Purser for whale context.

## Pattern: hot_deploy questions often also need incident_summary

If the user mentions "on fire" or "errors spiked" AND there's an active PagerDuty
incident, dispatch both V1 (Cooper) and V2 (Helm) in parallel. Cooper traces the code;
Helm traces the infrastructure. Their findings synthesize into a complete picture.
