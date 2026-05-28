import { type NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_KRAKEN_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = (await req.json()) as { message?: string; params?: Record<string, unknown> };
  const { message = "", params = {} } = body;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, params }),
    });

    if (!res.ok) {
      return NextResponse.json(
        { reply: "KRAKEN backend returned an error. Check that the API server is running." },
        { status: res.status }
      );
    }

    const data = (await res.json()) as { reply: string; voyage_id?: string };
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        reply: "Unable to reach the KRAKEN API. Start the Python backend with `kraken api:serve`.",
      },
      { status: 503 }
    );
  }
}
