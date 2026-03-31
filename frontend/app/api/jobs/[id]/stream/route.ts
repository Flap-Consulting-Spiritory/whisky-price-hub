import { NextRequest } from "next/server";

const API = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const upstream = await fetch(`${API}/api/jobs/${params.id}/stream`, {
    headers: { Accept: "text/event-stream" },
    // @ts-expect-error — Node.js fetch duplex
    duplex: "half",
  });

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
