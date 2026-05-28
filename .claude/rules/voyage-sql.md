---
description: SQL conventions for voyage YAML templates (lazy-loads when editing voyages/)
paths: ["kraken/voyages/**", "sources/**"]
---

# Voyage SQL Rules

- Always name every column explicitly. No SELECT *.
- One column per line for readability.
- Always include a date filter on time-series tables (sentry, datadog, github.deployments).
- Always specify INNER JOIN vs LEFT JOIN explicitly — never bare JOIN.
- Always include LIMIT to prevent runaway results.
- Use window functions (LAG, LEAD, ROW_NUMBER) for trend analysis.
- Use CTEs (WITH clauses) for queries spanning >5 sources.
- Format SQL one clause per line. SQL is documentation; readability matters.
- No SELECT * in voyage definitions. Ever.
- Always JOIN at least 3 Coral sources. A voyage touching 1-2 sources is not a voyage.
- Column types in source specs use Coral types: Utf8 | Int64 | Float64 | Boolean | Date | Timestamp.
- Nested API fields use double underscores: assignee__name maps to assignee.name in JSON.
