# Bosun — Known Patterns

## Learned from past sprint health analyses

---

## Pattern: issues with >5 Slack mentions but 0 PRs are spec-ambiguous, not blocked

When an issue has many Slack mentions but no open PR, the team is likely debating
scope, not blocked on a dependency. Suggest a spec clarification session with PM
rather than pairing or escalation.

## Pattern: Jira mirror status is often stale by 1-2 hours

The jira source caches responses. If Jira status is "blocked" but Linear shows
"in_review", trust Linear as the more recent source. Note the discrepancy in the finding.

## Pattern: "stuck_for" should use actual timestampdiff, not date trunc

Use `NOW() - l.updated_at` for exact duration, not `DATE_TRUNC('day', ...)`.
"Stuck for 4 days 3 hours" is more actionable than "stuck for 4 days".
