# Lookout — OSV Query Patterns Skill

## Efficient OSV.dev query patterns via Coral

The `osv` custom source exposes: `osv.vulnerabilities`, `osv.affected`, `osv.ranges`.

### Pattern 1: New CVEs in last 24h above threshold

```sql
SELECT
  v.id,
  v.summary,
  v.severity_score,
  v.published
FROM osv.vulnerabilities v
WHERE v.published > NOW() - INTERVAL '{{ hours_back }} hours'
  AND v.severity_type = 'CVSS_V3'
  AND CAST(v.severity_score AS DOUBLE) >= {{ severity_threshold }}
ORDER BY v.severity_score DESC;
```

### Pattern 2: Does this CVE affect our production packages?

```sql
SELECT
  v.id,
  a.package_name,
  a.ecosystem,
  a.introduced_version,
  a.fixed_version
FROM osv.vulnerabilities v
JOIN osv.affected a ON a.vulnerability_id = v.id
JOIN github.dependencies dep
  ON dep.package_name = a.package_name
 AND dep.ecosystem    = a.ecosystem
WHERE v.id = '{{ cve_id }}'
  AND dep.repo IN (SELECT DISTINCT repo FROM github.deployments
                   WHERE environment = 'production');
```

### Pattern 3: All CVEs for a package

```sql
SELECT v.id, v.summary, v.severity_score, a.introduced_version, a.fixed_version
FROM osv.vulnerabilities v
JOIN osv.affected a ON a.vulnerability_id = v.id
WHERE a.package_name = '{{ package_name }}'
  AND a.ecosystem    = '{{ ecosystem }}'
  AND v.severity_type = 'CVSS_V3'
ORDER BY v.severity_score DESC;
```

### Performance notes
- Always filter by `v.published` date range — OSV has hundreds of thousands of records
- Always filter by `v.severity_type = 'CVSS_V3'` to exclude pre-CVSS3 records
- Always CAST `severity_score` to DOUBLE for numeric comparison (stored as string in OSV API)
- The `osv.affected` table is the join table — never query `osv.vulnerabilities` alone
  when you need package exposure data
