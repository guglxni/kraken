# sources/local-codebase — Local Filesystem as SQL

Coral source spec that exposes a local codebase as queryable SQL tables. No
external API calls are made — all data is read directly from the local
filesystem and git object store. Enables KRAKEN's Cooper (coding debugger) and
Helm (SRE) agents to run federated queries that JOIN codebase structure and
history against live observability data from Sentry, Datadog, and GitHub.

**Authentication:** None (local filesystem).

**Backend:** File (Coral file backend reads JSONL pre-processed by KRAKEN).

**Bounty eligible:** Yes — $100 + $50 charity (see PROPOSAL.md)

---

## Tables

| Table | Pre-processing required | Key Columns |
|---|---|---|
| `files` | `kraken source preprocess local-codebase files` | `path`, `extension`, `content`, `mtime` |
| `diffs` | `kraken source preprocess local-codebase diffs` | `commit_sha`, `author_email`, `file_path`, `additions`, `deletions`, `created_at` |
| `symbols` | `kraken source preprocess local-codebase symbols` | `symbol_name`, `symbol_kind`, `language`, `file_path`, `signature` |

---

## Pre-processing

The file backend reads JSONL files pre-written by KRAKEN's preprocessor. Run:

```bash
# Index all files in the current directory
kraken source preprocess local-codebase files --path .

# Index git commit history (last 90 days by default)
kraken source preprocess local-codebase diffs --path . --days 90

# Parse symbols with tree-sitter
kraken source preprocess local-codebase symbols --path .
```

Output is written to `.kraken/` within the codebase path (gitignored).

---

## Example Coral SQL

### Find all Python files modified in the last 7 days with their sizes

```sql
SELECT
    path,
    size_bytes,
    mtime
FROM local_codebase.files
WHERE extension = 'py'
  AND mtime >= NOW() - INTERVAL '7 days'
ORDER BY
    mtime DESC
```

### Correlate recent commits with Sentry errors (Cooper debugging voyage)

```sql
SELECT
    d.commit_sha,
    d.author_email,
    d.message,
    d.file_path,
    d.created_at       AS commit_time,
    s.title            AS sentry_error,
    s.first_seen,
    s.times_seen
FROM local_codebase.diffs AS d
INNER JOIN sentry.issues AS s
    ON s.first_seen >= d.created_at
    AND s.first_seen <= d.created_at + INTERVAL '2 hours'
WHERE d.created_at >= NOW() - INTERVAL '48 hours'
  AND s.status = 'unresolved'
ORDER BY
    d.created_at DESC,
    s.times_seen DESC
LIMIT 50
```

### Find all functions that reference a specific dependency

```sql
SELECT
    sym.file_path,
    sym.symbol_name,
    sym.symbol_kind,
    sym.start_line,
    sym.signature
FROM local_codebase.symbols AS sym
WHERE sym.symbol_kind IN ('import', 'function')
  AND sym.signature LIKE '%stripe%'
ORDER BY
    sym.file_path,
    sym.start_line
```

---

## How the file backend works

Coral's `file` backend reads JSONL files from disk using the path and glob
pattern specified in `source.location`. Each JSON object in the JSONL becomes
one row. Column names map directly to JSON keys; double underscores (`__`)
denote nested path access.

The KRAKEN preprocessor (`kraken source preprocess`) is responsible for:
- Walking the filesystem and emitting one JSON object per file to
  `.kraken/files.jsonl`
- Running `git log --numstat` and parsing the output to
  `.kraken/git-log.jsonl`
- Running tree-sitter on supported language files and emitting symbol rows
  to `.kraken/symbols.jsonl`

The preprocessor is idempotent and incremental — it only re-indexes files
whose `mtime` is newer than the last run.
