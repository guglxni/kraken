# Cooper — PR Drafting Skill

## PR template

Every PR draft Cooper produces follows this template:

```markdown
## Bug Report

**Severity:** P{1|2|3}
**Deploy SHA:** {sha}
**Introduced by:** {author} in PR #{pr_number}

## Root Cause

{1-3 sentence description}. Evidence:
- SQL query: `{coral_sql snippet}`
- Stack trace pattern: `{error function signature}`
- Symbol last changed: `{file}:{line}` in commit `{sha[:8]}`

## Proposed Fix

{brief description}

```diff
{unified diff — 10-20 lines max}
```

## Test to Add

```{language}
{test function that would have caught this}
```

## Checklist

- [ ] Tests pass locally
- [ ] No production code modified outside this fix
- [ ] Reviewed by at least one other engineer before merge
- [ ] This PR description has been reviewed for PII (no customer data in comments)
```

## Quality bar for PR drafts

1. Never include customer names, emails, or PII in the diff or description
2. Keep the diff focused — one bug fix per PR
3. The test must be a real assertion, not a placeholder
4. The "introduced by" claim must be backed by SQL evidence from the finding
5. Always end with "tests must pass before merge"
