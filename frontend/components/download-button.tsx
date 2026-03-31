"use client";

import { Download } from "lucide-react";
import { getDownloadUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DownloadButtonProps {
  jobId: string;
  enabled: boolean;
}

export function DownloadButton({ jobId, enabled }: DownloadButtonProps) {
  const handleDownload = () => {
    if (!enabled) return;
    window.location.href = getDownloadUrl(jobId);
  };

  return (
    <button
      onClick={handleDownload}
      disabled={!enabled}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border",
        enabled
          ? "bg-accent hover:bg-accent/80 text-black border-accent cursor-pointer"
          : "bg-muted text-muted-foreground border-border cursor-not-allowed opacity-50"
      )}
      title={enabled ? "Download enriched CSV" : "Available when job is completed"}
    >
      <Download className="w-4 h-4" />
      Download Enriched CSV
    </button>
  );
}
