"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { getJob } from "@/lib/api";
import type { Job } from "@/lib/types";
import { StatsCards } from "@/components/stats-cards";
import { ProgressFeed } from "@/components/progress-feed";
import { ResultsTable } from "@/components/results-table";
import { DownloadButton } from "@/components/download-button";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/utils";

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchJob = useCallback(async () => {
    try {
      const data = await getJob(id);
      setJob(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchJob();
    // Poll while running
    const interval = setInterval(() => {
      fetchJob();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchJob]);

  const handleDone = useCallback(() => {
    fetchJob();
    setRefreshKey((k) => k + 1);
  }, [fetchJob]);

  if (loading || !job) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isActive = job.status === "running" || job.status === "pending";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1
              className="text-xl font-bold truncate max-w-lg"
              title={job.original_filename}
            >
              {job.original_filename}
            </h1>
            <StatusBadge status={job.status} />
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground pl-6">
            <span>Created {formatDate(job.created_at)}</span>
            {job.started_at && <span>Started {formatDate(job.started_at)}</span>}
            {job.finished_at && <span>Finished {formatDate(job.finished_at)}</span>}
          </div>
        </div>
        <DownloadButton jobId={id} enabled={job.status === "completed"} />
      </div>

      {/* Stats */}
      <StatsCards job={job} />

      {/* Log feed — live while active, historical when completed */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-foreground">Output</h2>
        <ProgressFeed jobId={id} onDone={handleDone} isCompleted={!isActive} />
      </section>

      {/* Results */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-foreground">Results</h2>
        <ResultsTable jobId={id} refreshKey={refreshKey} />
      </section>
    </div>
  );
}
