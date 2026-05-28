# Cooper — Hot Deploy (V1) Playbook

## Execution steps

1. **Run hot_deploy voyage.** Parameters: `hours_back=24`, `error_threshold=10`.
   The voyage returns rows grouped by (sha, pr_title, author) with `new_errors`,
   `p99_delta`, `touched_symbols`, `last_oncall_message`.

2. **Identify the hottest deploy.** Sort by `new_errors DESC`. Focus on the top row.

3. **Drill into symbols.** For each symbol in `touched_symbols`, query
   `local_codebase.symbols WHERE name = ANY(touched_symbols)` to get the file path
   and function signature. This confirms the symbol exists in the current codebase.

4. **Trace the error pattern.** Query `sentry.issues WHERE sha = {deploy_sha}` to
   get the stack traces. Identify which function appears most in the traces.

5. **Draft the finding.** Include:
   - Deploy SHA and PR title
   - Author name
   - Error count and p99 delta (numbers, not vague descriptions)
   - The specific function that's failing (from local_codebase.symbols)
   - A hypothesis for the root cause
   - A proposed fix as a diff snippet
   - The test that would have caught this

6. **Write to kraken.findings.** The Quartermaster synthesizes from this.

## Evidence requirements
Every finding must include at least:
- 1 SQL snippet showing the error correlation
- 1 SQL snippet showing the symbol lookup
- The deploy SHA (full 40-char hash)
- The author's GitHub login
