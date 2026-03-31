import { NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export async function GET() {
  const res = await fetch(`${API}/api/jobs`, { cache: "no-store" });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
