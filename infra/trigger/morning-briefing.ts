import { schedules } from "@trigger.dev/sdk/v3";

// ── Morning Briefing — KRAKEN Scheduled Voyage ─────────────────────────────
// Fires daily at 7:00 AM IST (01:30 UTC).
// Triggers the risk_heatmap voyage via the KRAKEN API.
// The Quartermaster then routes findings to the appropriate specialist agents.
//
// Cron expression: "30 1 * * *" = minute 30, hour 1 UTC, every day
// ─────────────────────────────────────────────────────────────────────────────

const KRAKEN_API_URL = process.env.KRAKEN_API_URL ?? "http://localhost:8080";

export const morningBriefing = schedules.task({
  id: "morning-briefing",
  // 7:00 AM IST = 01:30 UTC
  cron: "30 1 * * *",
  run: async (_payload, { ctx }) => {
    const voyageId = `mbr-${ctx.run.id}`;

    const response = await fetch(`${KRAKEN_API_URL}/api/voyages/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Internal service key — never expose externally
        "X-Kraken-Key": process.env.KRAKEN_INTERNAL_KEY ?? "",
      },
      body: JSON.stringify({
        voyage: "risk_heatmap",
        voyage_id: voyageId,
        params: {
          // Rolling 24-hour window from the moment the cron fires
          look_back_hours: 24,
          source: "morning_briefing",
        },
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Morning briefing voyage failed: HTTP ${response.status} — ${body}`
      );
    }

    const result = await response.json();

    return {
      voyage_id: voyageId,
      trigger_run_id: ctx.run.id,
      status: response.status,
      findings_count: result.findings_count ?? null,
      plans_count: result.plans_count ?? null,
    };
  },
});
