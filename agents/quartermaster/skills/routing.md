# Quartermaster Routing Skill

## Decision tree: question type → voyage kind → target agent

Use this skill before every dispatch. Read the user's question and match it to the
closest registered voyage. If no match, respond with the two closest matches and ask
for clarification.

---

## Voyage classification rules

### V1 — hot_deploy → cooper
**Triggers:** keywords like "deployed", "shipping", "on fire", "errors spiked",
"regression", "PR introduced", "who broke", "last 24 hours errors"

**Discriminator questions:**
- Does the question involve a recent code change causing current errors? → hot_deploy
- Does the question ask about root cause of a *known* incident? → incident_summary (V2)

**Example questions:**
- "What did we ship today that broke prod?"
- "Sentry errors are up 4x since the 3pm deploy — what changed?"
- "Which PR introduced the dashboard-api latency spike?"

**Required params:** `hours_back` (default 24)

---

### V2 — incident_summary → helm
**Triggers:** keywords like "PagerDuty", "incident", "on-call", "paged", "outage",
"SLA breach", "auto-summarize", "what happened"

**Discriminator questions:**
- Does the question reference a specific incident ID or on-call page? → incident_summary
- Is the incident already in PagerDuty? → incident_summary
- Is the question about which deploys caused errors more generally? → hot_deploy (V1)

**Example questions:**
- "Summarize PagerDuty incident INC-4821"
- "Auto-summarize the current P1 with all context"
- "We were paged at 3am — what was the blast radius?"

**Required params:** `incident_id` OR `hours_back` (default 2)

---

### V3 — stuck_sprint → bosun
**Triggers:** keywords like "sprint", "slipping", "blocked", "in-progress too long",
"no PR", "spec ambiguity", "dependency", "Linear", "Jira", "delivery risk"

**Discriminator questions:**
- Does the question ask about work item health or sprint velocity? → stuck_sprint
- Does the question ask about a code-level bug? → hot_deploy (V1)

**Example questions:**
- "Why is this sprint going to slip?"
- "Which tickets have been in-progress for over 3 days with no PR?"
- "Show me everything that's blocked and who owns the blocker"

**Required params:** `sprint_id` OR `days_back` (default 7), `stale_days` (default 3)

---

### V4 — angry_whales → purser
**Triggers:** keywords like "customer", "Intercom", "open tickets", "unhappy",
"churning", "support", "enterprise", "high-MRR", "angry"

**Discriminator questions:**
- Is the question about multiple customers or a queue of tickets? → angry_whales
- Is the question about one specific executive email? → exec_escalation (V6)
- Does the question include MRR-weighting concern? → angry_whales

**Example questions:**
- "Which high-value customers have open support tickets with active errors?"
- "Show me our whale accounts that are churning right now"
- "Which enterprise customers had the worst experience this week?"

**Required params:** `mrr_threshold` (default 5000), `hours_back` (default 24)

---

### V5 — fresh_cve → lookout
**Triggers:** keywords like "CVE", "vulnerability", "security", "OSV", "exploit",
"CVSS", "patch", "dependency exposure", "SBOM"

**Discriminator questions:**
- Does the question ask about new vulnerabilities in production? → fresh_cve
- Does the question ask about a vulnerability that was *already* flagged? → stigmergic_self_ref (V8)

**Example questions:**
- "What new CVEs landed in the last 24h that we're exposed to?"
- "Did any critical vulnerabilities ship in yesterday's deploy?"
- "Show me all CVSS ≥ 7 issues in our production dependencies"

**Required params:** `hours_back` (default 24), `severity_threshold` (default 7.0)

---

### V6 — exec_escalation → purser (HERO VOYAGE)
**Triggers:** CEO email, executive email, "URGENT", Gmail thread from a whale customer,
"churning", single-customer deep-dive with MRR context

**Discriminator questions:**
- Is this triggered by a specific email from a known customer? → exec_escalation
- Does it require drafting a CEO reply? → exec_escalation
- Is it about multiple customers in a queue? → angry_whales (V4)

**Example questions:**
- "Acme just emailed me saying they're churning — what's happening?"
- "Respond to this Gmail from the CEO of Globex ($240K ARR)"
- "I got a message from enterprise@bigcorp.com about downtime — full context please"

**Required params:** `sender_email`, `hours_back` (default 6), `mrr_threshold` (default 10000)

**HERO DEMO NOTE:** This is the primary demo voyage. Do not modify its routing without
explicit approval. The hero demo flow: Gmail → Reef Map animates → Spyglass shows receipts →
Bench-O-Bot fires.

---

### V7 — risk_heatmap → helm
**Triggers:** "morning briefing", "risk summary", "daily standup", "what's on fire",
"heatmap", "overview", "what should I look at first", scheduled 08:30 cron

**Discriminator questions:**
- Is the question asking for a broad risk overview across all domains? → risk_heatmap
- Is it focused on a specific incident? → incident_summary (V2)

**Example questions:**
- "Give me the morning briefing"
- "What are the top risks across our platform right now?"
- "Risk heatmap for the last 24 hours"

**Required params:** `hours_back` (default 24), `top_n` (default 50)

---

### V8 — stigmergic_self_ref → lookout
**Triggers:** "was this CVE already flagged", "prior findings", "self-reference",
"lookout already saw this", "duplicate CVE", "recurring vulnerability"

**Discriminator questions:**
- Is the question asking whether KRAKEN already found this CVE before? → stigmergic_self_ref
- Is it a new CVE check? → fresh_cve (V5)

**Example questions:**
- "Did we flag this CVE before and then deploy the vulnerable package anyway?"
- "Show me CVEs in production that lookout already warned us about"
- "Which vulnerabilities are we ignoring from prior reports?"

**Required params:** none required (self-referential — reads kraken.findings)

---

## Multi-voyage dispatch rules

Dispatch to multiple agents in parallel when:
1. The question spans both SRE (helm) AND code (cooper) — dispatch both V1 and V2
2. The question is an exec escalation that also has CVE exposure — dispatch V6 (purser) + V5 (lookout)
3. The morning briefing is requested — dispatch V7 (helm) always; optionally V4 (purser) for whale status

**Maximum parallel dispatches:** 3. If more than 3 voyages would be needed, ask the user to scope the question.

---

## When no voyage matches

Respond with:
```
I don't have a voyage for this question. Closest registered voyages:
1. [voyage_kind] — [one-line description]
2. [voyage_kind] — [one-line description]

Would you like me to run one of these, or should this be a new voyage?
```

Do not attempt to run a one-off SQL query. Do not invent a voyage kind.
