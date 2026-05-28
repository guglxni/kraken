# Purser — Executive Escalation (V6) Playbook — HERO DEMO

## This is the hero demo voyage. Handle with care.

## Execution steps

1. **Run exec_escalation voyage.** Parameters: `hours_back=6`, `mrr_threshold=10000`.
   If a specific sender_email is provided, add a WHERE filter.
   The voyage returns all columns defined in exec_escalation.yaml.

2. **Build the escalation brief.** For each row:
   - Customer name and MRR (required — no "customer X" vagueness)
   - Active error count and current p99 latency (with baseline for comparison)
   - Last deploy SHA and timestamp
   - Open incident count
   - Unpatched CVE count (CVSS ≥ 7.0 in last 7 days)
   - Suggested actions from this menu: draft_reply, page_oncall, rollback, create_ticket

3. **Check Cooper/Helm findings.** Before drafting the reply, query:
   `SELECT payload FROM kraken.findings WHERE kind IN ('hot_deploy_brief', 'incident_brief')
   AND created_at > NOW() - INTERVAL '1 hour'`
   If Cooper or Helm have already found the root cause, reference it in the reply.

4. **Draft the CEO reply.** Via `composio_draft_email`. Template:
   ```
   Subject: Re: {email_subject}

   Dear {contact_name},

   Thank you for reaching out. We are aware of the issue affecting your {service_name}
   and are actively working on a resolution.

   Current status: {root_cause if known, otherwise "under active investigation"}
   Error rate: {active_errors} errors in the last 24 hours
   Last deploy: {deployed_at} — {is or is not} suspected as the cause
   ETA for resolution: {only if Cooper/Helm have confirmed a fix}

   I will personally follow up within {1 hour for Tier 1, 4 hours for Tier 2}.

   [DRAFT — REQUIRES ANCHOR APPROVAL BEFORE SENDING]
   ```

5. **Write finding.** Structured as `EscalationBrief`.

## Critical rules for this voyage

- Never send the email. Always use test mode. Always require Anchor approval.
- Never promise a fix ETA unless Cooper or Helm has confirmed a fix in kraken.findings.
- Always include MRR. This is what makes the escalation brief actionable.
- The email draft goes into `composio_draft_email` ONLY — never into a Slack message or
  any other channel without explicit user instruction.
