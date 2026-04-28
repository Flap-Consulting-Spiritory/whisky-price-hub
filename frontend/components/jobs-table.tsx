"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { deleteJob, listJobs } from "@/lib/api";
import type { Job } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import { Loader2, Trash2 } from "lucide-react";

export function JobsTable() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const data = await listJobs();
      setJobs(data);
    } catch {
      // silently fail on poll errors
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (job: Job) => {
    const confirmed = window.confirm(
      `Delete this run? This removes all results and the input/output CSVs from the server.\n\nFile: ${job.original_filename}`
    );
    if (!confirmed) return;
    setDeletingId(job.id);
    try {
      await deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No jobs yet — upload a CSV to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">File</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Bottles</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Scraped</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Failed</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Skipped</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Created</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider w-12"></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job, i) => (
            <tr
              key={job.id}
              className={`border-b border-border hover:bg-muted/20 transition-colors ${
                i === jobs.length - 1 ? "border-b-0" : ""
              }`}
            >
              <td className="px-4 py-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="font-medium text-foreground hover:text-accent transition-colors truncate max-w-[200px] block"
                  title={job.original_filename}
                >
                  {job.original_filename}
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-4 py-3 text-right text-muted-foreground">{job.total_bottles}</td>
              <td className="px-4 py-3 text-right text-accent font-medium">{job.scraped}</td>
              <td className="px-4 py-3 text-right text-destructive font-medium">{job.failed}</td>
              <td className="px-4 py-3 text-right text-muted-foreground">{job.skipped}</td>
              <td className="px-4 py-3 text-muted-foreground text-xs">{formatDate(job.created_at)}</td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => handleDelete(job)}
                  disabled={
                    deletingId === job.id ||
                    job.status === "running" ||
                    job.status === "pending"
                  }
                  title={
                    job.status === "running" || job.status === "pending"
                      ? "Wait for the run to finish before deleting"
                      : "Delete this run"
                  }
                  className="text-muted-foreground hover:text-destructive disabled:opacity-30 disabled:cursor-not-allowed transition-colors p-1"
                  aria-label="Delete run"
                >
                  {deletingId === job.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
