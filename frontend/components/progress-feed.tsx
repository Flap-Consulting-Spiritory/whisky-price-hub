"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { getStreamUrl } from "@/lib/api";
import type { SSEEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

interface LogLine {
  id: number;
  text: string;
  type: "info" | "success" | "error" | "warn" | "system";
  ts: string;
}

interface ProgressFeedProps {
  jobId: string;
  onDone?: () => void;
}

let _lineId = 0;

export function ProgressFeed({ jobId, onDone }: ProgressFeedProps) {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [connected, setConnected] = useState(false);
  const [finished, setFinished] = useState(false);
  const finishedRef = useRef(false);

  const addLine = useCallback((text: string, type: LogLine["type"] = "info", ts = "") => {
    setLines((prev) => [...prev, { id: ++_lineId, text, type, ts }]);
  }, []);

  useEffect(() => {
    finishedRef.current = false;
    const url = getStreamUrl(jobId);
    const es = new EventSource(url);

    es.onopen = () => {
      setConnected(true);
      addLine("Connected to scraper stream.", "system");
    };

    es.onmessage = (e) => {
      if (!e.data || e.data === "{}") return;
      try {
        const event: SSEEvent = JSON.parse(e.data);

        if (event.type === "progress") {
          const icon =
            event.status === "success" ? "✓" : event.status === "failed" ? "✗" : "–";
          const t = event.status === "success" ? "success" : event.status === "failed" ? "error" : "warn";
          addLine(
            `[${event.scraped}/${event.total}] ${icon} ${event.bottle_name || event.wb_id} (WB${event.wb_id}) — ${event.status}`,
            t,
            event.ts
          );
        } else if (event.type === "log") {
          const t = event.level === "error" ? "error" : event.level === "warn" ? "warn" : "info";
          addLine(event.msg, t, event.ts);
        } else if (event.type === "done") {
          addLine(
            `Job ${event.status}. Scraped: ${event.scraped} | Failed: ${event.failed} | Skipped: ${event.skipped}`,
            event.status === "completed" ? "success" : "error"
          );
          finishedRef.current = true;
          setFinished(true);
          es.close();
          onDone?.();
        }
      } catch {
        // skip malformed events
      }
    };

    es.onerror = () => {
      setConnected(false);
      if (!finishedRef.current) {
        addLine("Stream disconnected, reconnecting...", "warn");
        // Don't close — browser EventSource will auto-reconnect
      }
    };

    return () => es.close();
  }, [jobId, addLine, onDone]);

  const lineColor: Record<LogLine["type"], string> = {
    info: "text-zinc-400",
    success: "text-green-400",
    error: "text-red-400",
    warn: "text-yellow-400",
    system: "text-zinc-600",
  };

  return (
    <div className="rounded-lg border border-border bg-black overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card">
        <span className="text-xs font-mono text-muted-foreground">scraper output</span>
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              finished ? "bg-zinc-600" : connected ? "bg-green-500 animate-pulse" : "bg-yellow-500"
            )}
          />
          <span className="text-xs text-muted-foreground">
            {finished ? "finished" : connected ? "live" : "connecting..."}
          </span>
        </div>
      </div>
      <div className="h-72 overflow-y-auto p-4 font-mono text-xs space-y-0.5">
        {lines.map((line) => (
          <div key={line.id} className="flex gap-3">
            {line.ts && (
              <span className="text-zinc-700 shrink-0 w-16">{line.ts}</span>
            )}
            <span className={lineColor[line.type]}>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
