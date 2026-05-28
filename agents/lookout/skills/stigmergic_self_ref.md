# Lookout — Stigmergic Self-Reference (V8) Playbook

## What this voyage demonstrates

V8 is an architectural showpiece. It proves that KRAKEN's blackboard is not just
a write-once store — agents can JOIN their own past findings with live sources to
detect when a previously-flagged vulnerability is still present in production.

This is "stigmergy": indirect coordination through environmental state. Lookout
leaves a finding in the environment (kraken.findings); a later Lookout invocation
reads that mark and reacts to it, without any direct agent-to-agent call.

## Execution steps

1. **Run stigmergic_self_ref voyage.** No parameters required.

2. **Read the result.** Each row is a CVE that:
   - Was previously flagged by Lookout (in a prior voyage)
   - Is still present in a production deploy that was created AFTER the finding
   - Has a current CVSS score (which may have changed since first flag)

3. **Assess re-exposure risk.** For each row:
   - How long between first_flagged and still_in_prod_at?
   - Has the CVSS score changed (up or down)?
   - Was there a remediation attempt (check github.pulls) that didn't hold?

4. **Write elevated finding.** Mark the finding with `kind = 'cve_recurring'` and
   `priority = 'critical'` if still in production > 7 days after first flag.

5. **Document the self-referential loop.** Include in the finding's evidence:
   - The original finding_id that flagged the CVE
   - The deploy SHA that reintroduced the vulnerability
   - The time gap between flag and reintroduction

## Why this matters for the demo

V8 is the "closing of the loop" moment in the demo. It shows that KRAKEN's
SQL-blackboard architecture enables emergent behavior: agents build institutional
memory organically, and future agents benefit from past work without any
orchestration layer. This is the core thesis of stigmergic multi-agent coordination.
