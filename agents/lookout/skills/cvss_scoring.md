# Lookout — CVSS v3 Scoring Skill

## Interpreting CVSS v3 scores

### Score ranges

| Score | Severity | Action |
|---|---|---|
| 9.0–10.0 | Critical | Page on-call now; create P1 ticket |
| 7.0–8.9 | High | Create P2 ticket; patch within 24h |
| 4.0–6.9 | Medium | Create P3 ticket; patch within 7 days |
| 0.1–3.9 | Low | Track; patch in next sprint |
| 0.0 | None | Monitor |

### Vector string interpretation

CVSS v3 vector format: `CVSS:3.1/AV:{v}/AC:{c}/PR:{p}/UI:{u}/S:{s}/C:{c}/I:{i}/A:{a}`

Key fields for prioritization:
- `AV:N` (Network) = remotely exploitable — highest concern
- `AC:L` (Low complexity) = easy to exploit — elevate priority
- `PR:N` (No privileges required) = unauthenticated — highest concern
- `UI:N` (No user interaction) = fully automated — highest concern

### Exploit maturity enrichment

OSV provides `database_specific.severity` and `affected[].database_specific`.
Supplement with:
- EPSS score (Exploit Prediction Scoring System) if available
- CISA KEV (Known Exploited Vulnerabilities) catalog check

### Reporting format

Always report as:
```
CVE-2024-45490 (CVSS 9.1 CRITICAL)
Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
Package: fast-xml-parser@4.3.2 (npm)
Exploit maturity: proof-of-concept (as of {date})
Production deploy: {sha} deployed {timestamp}
```
