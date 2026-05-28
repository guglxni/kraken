# sources/osv — OSV.dev Vulnerability Database

Coral source spec for [OSV.dev](https://osv.dev), the open, distributed
vulnerability database that aggregates CVEs, GitHub Security Advisories
(GHSAs), PyPI advisories, Go vulnerability reports, Rust (RustSec), Maven,
npm, and many more.

**Authentication:** None. OSV.dev is fully public.

**Backend:** HTTP (`https://api.osv.dev/v1`)

**Bounty eligible:** Yes — $100 + $50 charity (see PROPOSAL.md)

---

## Tables

| Table | Rows | Key Columns |
|---|---|---|
| `vulnerabilities` | One per advisory | `id`, `summary`, `published`, `severity__0__score` |
| `affected` | One per (vuln, package) | `vulnerability_id`, `package__name`, `package__ecosystem` |
| `ranges` | One per (vuln, package, range event) | `vulnerability_id`, `type`, `introduced`, `fixed` |
| `references` | One per external link | `vulnerability_id`, `type`, `url` |
| `aliases` | One per cross-database ID | `vulnerability_id`, `alias` |

---

## Example Coral SQL

### Find all CRITICAL npm vulnerabilities published in the last 30 days

```sql
SELECT
    v.id,
    v.summary,
    v.published,
    v.severity__0__score,
    a.package__name,
    r.introduced,
    r.fixed
FROM osv.vulnerabilities AS v
JOIN osv.affected AS a
    ON a.vulnerability_id = v.id
JOIN osv.ranges AS r
    ON r.vulnerability_id = v.id
WHERE a.package__ecosystem = 'npm'
  AND v.database_specific__severity = 'CRITICAL'
  AND v.published >= NOW() - INTERVAL '30 days'
ORDER BY
    v.published DESC
LIMIT 100
```

### Fresh-CVE voyage: correlate vulnerabilities with deployed packages

```sql
SELECT
    v.id                              AS cve_id,
    v.summary,
    v.database_specific__severity     AS severity,
    a.package__name,
    a.package__ecosystem,
    r.introduced,
    r.fixed,
    f.path                            AS manifest_file,
    v.published
FROM osv.vulnerabilities AS v
JOIN osv.affected AS a
    ON a.vulnerability_id = v.id
JOIN osv.ranges AS r
    ON r.vulnerability_id = v.id
    AND r.type = 'SEMVER'
JOIN local_codebase.files AS f
    ON f.path LIKE '%package.json%'
    OR f.path LIKE '%requirements.txt%'
    OR f.path LIKE '%Cargo.toml%'
WHERE v.published >= NOW() - INTERVAL '7 days'
  AND v.database_specific__severity IN ('CRITICAL', 'HIGH')
ORDER BY
    v.published DESC
```

---

## OSV API Notes

- **Query endpoint:** `POST /v1/query` — query by package name + ecosystem.
  Coral maps filter pushdown for `package_name` and `ecosystem` to the POST
  body automatically.
- **Batch endpoint:** `POST /v1/querybatch` — not yet used; Coral parallelises
  single queries efficiently.
- **Single vuln lookup:** `GET /v1/vulns/{id}` — used for the `affected`,
  `ranges`, `references`, and `aliases` tables when filtering by
  `vulnerability_id`.
- **Rate limits:** No documented rate limit for public read access. Be
  conservative: Coral's per-source leaky bucket is set to 10 req/s for OSV.
- **Pagination:** Uses `page_token` cursor pagination on the query endpoint.

---

## Upstream PR

This spec is intended to be submitted to
[withcoral/coral](https://github.com/withcoral/coral) as a community source
contribution. Mirror the format of `sources/github/manifest.yaml` in that repo
before submitting.
