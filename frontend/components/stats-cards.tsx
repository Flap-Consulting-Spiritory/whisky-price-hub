import type { Job } from "@/lib/types";

interface StatsCardsProps {
  job: Job;
}

export function StatsCards({ job }: StatsCardsProps) {
  const progress =
    job.total_bottles > 0
      ? Math.round(((job.scraped + job.failed + job.skipped) / job.total_bottles) * 100)
      : 0;

  const cards = [
    {
      label: "Total Bottles",
      value: job.total_bottles,
      color: "text-foreground",
      bg: "border-border",
    },
    {
      label: "Scraped",
      value: job.scraped,
      color: "text-accent",
      bg: "border-green-900",
    },
    {
      label: "Failed",
      value: job.failed,
      color: "text-destructive",
      bg: "border-red-900",
    },
    {
      label: "Skipped",
      value: job.skipped,
      color: "text-muted-foreground",
      bg: "border-border",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className={`rounded-lg bg-card border ${card.bg} p-4`}
          >
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
              {card.label}
            </p>
            <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {(job.status === "running" || job.status === "pending") && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
