# KRAKEN

> One SQL query. Every system. Every voyage. The kraken sees what the org cannot.

KRAKEN is the canonical developer surface for [Coral](https://withcoral.com) — a federated query platform that gives engineering organizations a single SQL interface over every system they run.

Built for the [WeMakeDevs Pirates of the Coral-bean hackathon](https://www.wemakedevs.org/hackathons/coral) · Track 1: Enterprise Agent.

---

## The problem

The VP of Engineering at a mid-size SaaS company opens 8 tabs every morning: Linear, GitHub Insights, Sentry, Datadog, Slack, Intercom, PagerDuty, Confluence. 25-40 minutes of manual stitching. Repeated before every staff meeting, board meeting, and incident retro.

Every existing tool is a chatbot over its own vertical silo. None can execute the JOIN that the VP-Eng's brain executes manually every morning.

**KRAKEN replaces that with one Coral SQL query.**

---

## Architecture

```
Captain's Bridge (Next.js 15 + React 19 + CopilotKit)
        │ AG-UI protocol (SSE + WebSocket)
Agent Swarm (CrewAI Flows + PydanticAI)
  Quartermaster → Helm, Cooper, Bosun, Purser, Lookout
        │ MCP stdio
Coral (federated SQL runtime)
  21 bundled sources + 3 custom (osv, local-codebase, webhooks)
        │ kraken.findings Parquet blackboard
Infrastructure (Supabase + Langfuse + PostHog + Trigger.dev)
```

---

## Quick start

```bash
# Requirements: Python 3.12+, Node.js 20+, Docker, Coral CLI
git clone https://github.com/guglxni/kraken
cd kraken

# Start infrastructure
docker compose up -d

# Install Python dependencies
uv sync

# Install UI dependencies
cd ui && pnpm install && cd ..

# Add Coral sources (interactive)
coral source add --interactive github
coral source add --interactive sentry
coral source add --interactive stripe

# Add custom sources
coral source add --file sources/osv/manifest.yaml
coral source add --file sources/local-codebase/manifest.yaml

# Run a voyage
kraken voyage:run exec-escalation --sender ceo@acme.com

# Start the UI
cd ui && pnpm dev
# → http://localhost:3000
```

---

## Voyage library

| Voyage | Sources | Question |
|---|---|---|
| V1 Hot Deploy | github + sentry + datadog + slack + local-codebase | What shipped that's on fire? |
| V2 Incident Summary | pagerduty + github + datadog + statusgator + slack | Auto-summarize this incident |
| V3 Stuck Sprint | linear + jira + github + slack + confluence | Why is the sprint slipping? |
| V4 Angry Whales | intercom + stripe + sentry + grafana + slack | Which customers are escalating? |
| V5 Fresh CVE | **osv** + github + slack + notion | What new CVE is in our prod deps? |
| **V6 Exec Escalation** | **gmail** + intercom + stripe + sentry + datadog + github + osv | Why is the CEO escalating? (HERO) |
| V7 Risk Heatmap | all sources | Morning briefing |
| V8 Stigmergic Self-Ref | kraken.findings + github + osv | Agent JOINs its own past findings |

---

## Custom Coral source specs

- `sources/osv/` — OSV.dev vulnerability database
- `sources/local-codebase/` — local filesystem + git as SQL (tree-sitter)
- `sources/webhooks/` — real-time webhook deliveries as a queryable table

---

## License

Apache 2.0
