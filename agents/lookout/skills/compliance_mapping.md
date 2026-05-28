# Lookout — Compliance Mapping Skill

## Mapping findings to SOC 2 / ISO 27001 controls

Every Lookout finding includes compliance context so it doubles as an audit artifact.

### Control mapping table

| Finding type | SOC 2 control | ISO 27001 control | NIST CSF |
|---|---|---|---|
| CVE in production | CC7.2 | A.12.6.1 | DE.CM-8 |
| Unpatched dependency | CC7.1 | A.12.6.1 | ID.RA-1 |
| Security policy violation | CC5.2 | A.18.2.2 | PR.IP-12 |
| Recurring vulnerability | CC7.2, CC4.1 | A.12.6.1, A.16.1.3 | RS.AN-1 |

### Audit artifact format

```markdown
## Security Finding — Lookout KRAKEN

**Date:** {ISO 8601 timestamp}
**Voyage ID:** {voyage_id}
**Finding ID:** {finding_id}

### Vulnerability
- **CVE:** {cve_id}
- **CVSS:** {score} ({severity})
- **Package:** {package}@{version} ({ecosystem})
- **Production exposure:** Yes — deploy {sha} on {date}

### Compliance Controls Triggered
- SOC 2 CC7.2: System operations — vulnerability identified in production
- ISO 27001 A.12.6.1: Management of technical vulnerabilities
- NIST CSF DE.CM-8: Vulnerability scanning

### Evidence
{SQL query snippets}

### Remediation Status
- [ ] Ticket created: {ticket_id or "pending"}
- [ ] Patch available: {yes/no/unknown}
- [ ] Prior upgrade attempt: {yes/no — see {pr_url}}

### Approvals Required
This finding requires review by: Security Lead, Engineering Manager
```

### When to escalate to Legal/Compliance team

Escalate (via Quartermaster → Anchor approval) if:
- CVSS ≥ 9.0 AND exploit is actively in the wild (check CISA KEV)
- Customer data may be exposed (check Presidio PII scan results)
- Regulatory deadline is within 72 hours (GDPR Article 33 breach notification)
