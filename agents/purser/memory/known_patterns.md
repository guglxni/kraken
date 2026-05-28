# Purser — Known Patterns

## Learned from past customer escalation voyages

---

## Pattern: exec_escalation SQL returns multiple rows per Gmail sender

If a sender has multiple email addresses or aliases, the JOIN with intercom.contacts
can return multiple rows. Always GROUP BY g.subject, g."from" and take MAX(sub.mrr)
to avoid duplicate escalation briefs for the same customer.

## Pattern: stripe.subscriptions.metadata->>'org_id' may be NULL for older accounts

For Stripe subscriptions created before the org_id metadata was added, the LEFT JOINs
to sentry and datadog will return NULL. Report these as "no error data available" rather
than "0 errors" — the distinction matters for the CEO reply.

## Pattern: CEO replies should never include the word "bug"

Customer-facing language: "issue" or "service disruption", not "bug". This is a
tone standard that has come up in past email reviews.
