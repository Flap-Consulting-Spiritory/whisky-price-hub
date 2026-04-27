import type { Job, ResultsResponse } from "./types";

const BASE = "/api";

export async function uploadCSV(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${BASE}/jobs`);
  if (!res.ok) throw new Error(`Failed to list jobs: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Job not found: ${res.status}`);
  return res.json();
}

export async function getResults(
  jobId: string,
  status?: string
): Promise<ResultsResponse> {
  const url = status
    ? `${BASE}/jobs/${jobId}/results?status=${status}`
    : `${BASE}/jobs/${jobId}/results`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch results: ${res.status}`);
  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/download`;
}

export async function getJobLogs(
  jobId: string
): Promise<Array<{ ts: string; level: string; msg: string }>> {
  const res = await fetch(`${BASE}/jobs/${jobId}/logs`);
  if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`);
  return res.json();
}

export interface JobProgressEvent {
  type: "progress";
  ts: string;
  wb_id: string;
  bottle_name: string | null;
  status: "success" | "failed";
  avg_price: number | null;
  currency: string | null;
  scraped: number;
  failed: number;
  total: number;
}

export async function getJobProgress(jobId: string): Promise<JobProgressEvent[]> {
  const res = await fetch(`${BASE}/jobs/${jobId}/progress`);
  if (!res.ok) throw new Error(`Failed to fetch progress: ${res.status}`);
  return res.json();
}

export function getStreamUrl(jobId: string): string {
  const backend = process.env.NEXT_PUBLIC_API_URL;
  if (backend) return `${backend}/api/jobs/${jobId}/stream`;
  return `${BASE}/jobs/${jobId}/stream`;
}
