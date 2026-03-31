import { cn } from "@/lib/utils";

type Status = "pending" | "running" | "completed" | "failed";

const statusConfig: Record<Status, { label: string; className: string }> = {
  pending: {
    label: "Pending",
    className: "bg-zinc-800 text-zinc-400 border-zinc-700",
  },
  running: {
    label: "Running",
    className: "bg-yellow-950 text-yellow-400 border-yellow-800",
  },
  completed: {
    label: "Completed",
    className: "bg-green-950 text-green-400 border-green-800",
  },
  failed: {
    label: "Failed",
    className: "bg-red-950 text-red-400 border-red-800",
  },
};

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = statusConfig[status] ?? statusConfig.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border",
        cfg.className,
        className
      )}
    >
      {status === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
      )}
      {cfg.label}
    </span>
  );
}
