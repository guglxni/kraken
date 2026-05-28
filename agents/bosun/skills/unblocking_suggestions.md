# Bosun — Unblocking Suggestions Skill

## Template for action suggestions

Every suggestion follows this format:

```
[ISSUE_ID] stuck for {duration}: {one-line diagnosis}
Suggested action: {action_verb} {specific_target} — {rationale in ≤15 words}
```

## Action menu

### pair
Use when: engineer has been on an issue > 3 days with no PR open.
Template: "Pair {assignee} with another engineer on {module} — unfamiliar territory."

### escalate
Use when: blocking issue is owned by another team or an external vendor.
Template: "Escalate {blocking_issue} to {team_name} — {assignee} is unblocked once resolved."

### move
Use when: issue stuck > 5 days, no PR, unclear scope.
Template: "Move {issue_id} to next sprint — scope is unclear; needs refinement session."
Only use "move" if stuck_for > 5 days. Never suggest moving a ticket stuck < 3 days.

### spec
Use when: slack_mentions_7d > 5 and no spec doc linked.
Template: "Request spec clarification from PM for {issue_id} — {N} Slack threads, no doc."

### review
Use when: PR exists but hasn't been updated in > 2 days.
Template: "Tag a reviewer on PR #{pr_number} for {issue_id} — review lag {days} days."

## What to never do
- Never name specific engineers as blockers
- Never suggest "reassign to someone else" without the EM explicitly requesting it
- Never use the word "blocked" without specifying what the dependency is and who owns it
- Never suggest moving a ticket without noting it needs a refinement session
