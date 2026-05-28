# Bosun — Stuck Sprint (V3) Playbook

## Execution steps

1. **Run stuck_sprint voyage.** Parameters: `stale_days=3`, `sprint_id` (optional).
   Returns issues sorted by `stuck_for DESC`.

2. **Categorize by blocker type.** For each stuck issue:
   - `no_pr`: `open_prs = 0` — work hasn't started as a PR
   - `spec_ambiguity`: `slack_mentions_7d > 5` AND `spec_doc IS NULL` — undocumented contention
   - `dependency`: `jira_mirror_status = 'blocked'` — external dependency
   - `review_lag`: `open_prs > 0` AND `pr_last_updated > 2 days ago` — PR sitting unreviewed

3. **Calculate impact.** For each blocker: how many other issues depend on this one?
   Use `kraken_graph` to find dependencies if the graph source is available.

4. **Suggest unblocking actions.** One action per issue, from this menu:
   - `pair`: suggest pairing the assignee with a specific engineer who has context
   - `escalate`: escalate the dependency to a Staff Eng or external team
   - `move`: suggest moving to next sprint (only if stuck > 5 days with no progress)
   - `spec`: request spec clarification from PM (only if slack_mentions_7d > 5)
   - `review`: tag a specific reviewer (never by name — use role: "the PR reviewer")

5. **Write finding.** Structured as `SprintBrief`.

## Evidence requirements

Every blocker report must include:
- The issue identifier (e.g., ENG-4821)
- Exact stuck duration: "stuck for 4 days 3 hours" (from NOW() - updated_at)
- The specific dependency or blocker (not "waiting on someone")
- The suggested action (from the menu above)
