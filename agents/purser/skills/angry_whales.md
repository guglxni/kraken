# Purser — Angry Whales (V4) Playbook

## Execution steps

1. **Run angry_whales voyage.** Parameters: `mrr_threshold=5000`, `hours_back=24`.
   Returns open Intercom conversations sorted by `mrr DESC, active_errors DESC`.

2. **Triage by MRR weight.** Group results:
   - Tier 1: MRR > $50K — immediate action required
   - Tier 2: MRR $10K–$50K — same-day response required
   - Tier 3: MRR $5K–$10K — next-business-day response

3. **Check for exec email.** For each Tier 1 customer, check `gm.exec_email_subject`.
   If an exec email exists and is in INBOX, escalate to V6 (exec_escalation) via
   Quartermaster. Do not run V6 yourself — write to findings and let Quartermaster route.

4. **Draft Intercom notes.** For each Tier 1 customer with an open conversation,
   draft an internal note via `composio_create_intercom_note`. Note includes:
   - Active error count and last error seen
   - Grafana dashboard URL if available
   - Last engineering response timestamp
   - Suggested next step

5. **Write finding.** Include the full customer list, sorted by MRR × active_errors
   as a composite priority score.

## Evidence requirements

Every whale entry must include MRR (exact number), active error count, and the
conversation ID. Never use vague descriptions like "several errors".
