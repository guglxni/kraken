# Cooper — Tree-Sitter Parse Skill

## Using local_codebase.symbols

The `local_codebase` Coral source parses the local repo with tree-sitter and exposes:
- `local_codebase.files` — all files with path, extension, line count
- `local_codebase.symbols` — all functions/classes with name, file, start_line, end_line
- `local_codebase.diffs` — git log with changed files per commit

### Query pattern: find which PR last touched a symbol

```sql
SELECT
  sym.name,
  sym.file,
  sym.start_line,
  d.sha,
  d.message,
  d.author
FROM local_codebase.symbols sym
JOIN local_codebase.diffs d
  ON d.file = sym.file
WHERE sym.name = '{{ symbol_name }}'
ORDER BY d.committed_at DESC
LIMIT 1;
```

### Query pattern: find all symbols touched by a PR's changed files

```sql
SELECT DISTINCT
  sym.name,
  sym.file
FROM local_codebase.symbols sym
WHERE sym.file = ANY(ARRAY[{{ changed_files_list }}]);
```

### Rules
- Always verify the symbol exists before including it in a finding
- Use `LIKE` matching for symbol names when exact name is uncertain
- Changed files come from `github.pulls.changed_files` (array column)
