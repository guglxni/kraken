# Bosun — Dependency Graph Skill

## Using kraken_graph for issue dependencies

When the kraken_graph source is available, query issue dependencies directly:

```sql
SELECT
  rel.from_id   AS blocked_issue,
  rel.to_id     AS blocking_issue,
  rel.kind      AS dependency_type,
  ent.label     AS blocking_issue_title
FROM kraken_graph.relationships rel
JOIN kraken_graph.entities ent
  ON ent.id = rel.to_id
WHERE rel.from_id = '{{ issue_id }}'
  AND rel.kind IN ('blocks', 'depends_on')
ORDER BY rel.created_at DESC;
```

## Fallback (without kraken_graph)

When kraken_graph is not available, infer dependencies from Jira mirror status:

```sql
SELECT j.external_id, j.status, j.blocking_issues
FROM jira.tickets j
WHERE j.external_id = '{{ issue_id }}'
  AND j.status = 'blocked';
```

## Output format

Report dependencies as:
```
ENG-4821 depends on EXT-301 (owned by Platform team, ETA unknown)
ENG-4821 depends on ENG-4799 (owned by @alice, currently in review)
```

Never report a dependency without naming who owns the blocking issue.
