# Purser — Email Drafting Skill

## CEO reply tone and format

KRAKEN email drafts are written from the perspective of the VP of Engineering or CEO.
The tone is: direct, empathetic, data-grounded, action-oriented.

### Tone rules
- Never use jargon the customer wouldn't understand
- Never make promises without evidence
- Always acknowledge the impact to the customer ("we understand this affected your team")
- Never use passive voice: "errors were introduced" → "our deploy on {date} introduced errors"
- Sign with the appropriate executive name (pulled from Intercom contact data)

### Length rules
- First paragraph: acknowledgment and current status (2 sentences max)
- Second paragraph: root cause if known, investigation status if not (3 sentences max)
- Third paragraph: next steps with timestamps (2 sentences max)
- Sign-off: name, title, direct contact (if appropriate)

### Never include in draft emails
- Internal ticket IDs (ENG-4821 etc.) — use description instead
- SQL query output verbatim — synthesize to natural language
- CVE IDs — too technical; say "security vulnerability" instead
- Dollar MRR figures — the customer knows their own contract
- Other customer names — never mention blast radius in customer emails

### Quality gate checklist (always run before writing finding)
- [ ] No PII beyond the recipient's own name and company
- [ ] No promises that aren't backed by kraken.findings evidence
- [ ] Subject line matches the original email's subject (Re: prefix)
- [ ] "DRAFT — REQUIRES ANCHOR APPROVAL" footer present
- [ ] Test mode flag confirmed in composio_draft_email call
