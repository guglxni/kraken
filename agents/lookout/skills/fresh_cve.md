# Lookout — Fresh CVE in Production (V5) Playbook

## Execution steps

1. **Run fresh_cve voyage.** Parameters: `hours_back=24`, `severity_threshold=7.0`.
   Returns CVEs joined with production deploys, PR authors, and policy docs.

2. **Assess each CVE.** For each row:
   - CVSS v3 score and vector string (base, temporal, environmental)
   - Exploit maturity: "proof-of-concept", "functional", "high" (from OSV data)
   - Production exposure: is the affected package version in a production deploy?
   - Policy doc: does a Notion security policy reference this package or CVE type?

3. **Check past upgrade attempts.** For each affected package, query:
   ```sql
   SELECT pr.number, pr.title, pr.state, pr.merged_at
   FROM github.pulls pr
   WHERE pr.title LIKE '%{package_name}%upgrade%'
      OR pr.title LIKE '%bump%{package_name}%'
   ORDER BY pr.created_at DESC LIMIT 3;
   ```
   If an upgrade was attempted and reverted, note the reason.

4. **Check prior Lookout findings.** Query `kraken.findings WHERE agent = 'lookout'
   AND payload->>'cve_id' = '{cve_id}'`. If found, this is a recurring vulnerability
   (V8 pattern) — elevate priority.

5. **Write finding.** Structured as `CVEBrief`. Map to compliance controls.

## Compliance mapping

For every CVE finding, include:
- SOC 2 control: CC7.2 (System Operations) for production exposure
- ISO 27001 control: A.12.6.1 (Management of technical vulnerabilities)
- NIST CSF function: DE.CM-8 (Vulnerability scans are performed)

## Evidence requirements

Every CVE finding must include: CVE ID, CVSS score + vector, package + version,
deploy SHA that introduced it, and the Notion policy doc if one exists.
