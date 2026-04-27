import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const res = await fetch(`${API}/api/jobs/${params.id}/logs`, { cache: "no-store" });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
