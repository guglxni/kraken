# Lookout — Known Patterns

## Learned from past security investigations

---

## Pattern: CAST(severity_score AS DOUBLE) is required in OSV joins

The OSV source returns severity_score as a string. Numeric comparisons (>= 7.0) will
silently return wrong results without the explicit CAST. Always use:
`CAST(v.severity_score AS DOUBLE) >= {{ severity_threshold }}`

## Pattern: github.dependencies is populated from dependency graph API, not lockfile

The github.dependencies Coral table reads from GitHub's dependency graph API.
This covers package.json, requirements.txt, go.mod, Cargo.toml, etc. but NOT
lockfiles. A package that appears in a lockfile but not the manifest may not appear.
Flag this limitation in CVE findings when the affected package is a transitive dep.

## Pattern: notion.pages security-policy tag search uses @> array operator

Querying Notion security policies: `WHERE n.tags @> ARRAY['security-policy']`
The `@> ARRAY['security-policy']` syntax is DuckDB's array containment operator.
Do not use `= 'security-policy'` — that would only match single-element tag arrays.
