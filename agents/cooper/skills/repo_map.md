# Cooper — Repo Map Skill

## Using Aider-style repo map for context

Before drafting a fix, build a mental map of the affected module:

1. Query `local_codebase.files WHERE path LIKE '%{module_path}%'` to get file list
2. Query `local_codebase.symbols WHERE file LIKE '%{module_path}%'` to get symbol list
3. Identify call graph: which symbols call the failing symbol?

### Call graph SQL pattern

```sql
-- Find callers of a function (via simple text search in symbols)
SELECT
  caller.name   AS caller_symbol,
  caller.file   AS caller_file,
  caller.start_line
FROM local_codebase.symbols caller
WHERE caller.body LIKE '%{{ target_symbol }}%'
  AND caller.name != '{{ target_symbol }}'
ORDER BY caller.file, caller.start_line;
```

### Repo map output format

```
{module_path}/
├── {file1}.{ext}
│   ├── {ClassName}
│   │   ├── {method_name}(args) → return_type  ← FAILING HERE
│   │   └── {other_method}(args)
│   └── {standalone_function}(args)
└── {file2}.{ext}
    └── ...
```

This map goes into the PR description as context for reviewers.
