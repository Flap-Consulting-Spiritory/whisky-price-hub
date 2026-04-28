"use client";

import { useEffect, useState } from "react";
import { getResults } from "@/lib/api";
import type { BottleResult, TopListing } from "@/lib/types";
import { formatPrice, cn } from "@/lib/utils";

interface ResultsTableProps {
  jobId: string;
  refreshKey?: number;
}

type TabKey = "all" | "success" | "failed" | "skipped_no_id";

const TABS: { key: TabKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "success", label: "Success" },
  { key: "failed", label: "Failed" },
  { key: "skipped_no_id", label: "No WB ID" },
];

export function ResultsTable({ jobId, refreshKey = 0 }: ResultsTableProps) {
  const [tab, setTab] = useState<TabKey>("all");
  const [results, setResults] = useState<BottleResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const statusParam = tab === "all" ? undefined : tab;
    getResults(jobId, statusParam)
      .then((data) => {
        setResults(data.items);
        setTotal(data.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [jobId, tab, refreshKey]);

  const parseListings = (raw: string | null): TopListing[] => {
    if (!raw) return [];
    try { return JSON.parse(raw); } catch { return []; }
  };

  return (
    <div className="space-y-3">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              tab === t.key
                ? "border-accent text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {t.label}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-muted-foreground pr-2">
          {total} row{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-8 text-muted-foreground text-sm">Loading...</div>
      ) : results.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">No results.</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">#</th>
                <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">Bottle</th>
                <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">WB ID</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">Client Ask</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">WB Avg (EUR)</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">WB Avg (orig)</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">WB Low (EUR)</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">WB High (EUR)</th>
                <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">vs WB</th>
                <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">Listings</th>
                <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">Shops</th>
                <th className="px-3 py-2.5 text-left font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const listings = parseListings(r.wb_top_listings);
                return (
                  <tr key={r.id} className="border-b border-border last:border-b-0 hover:bg-muted/10">
                    <td className="px-3 py-2.5 text-muted-foreground">{r.row_index + 1}</td>
                    <td className="px-3 py-2.5 max-w-[180px]">
                      <div className="font-medium text-foreground truncate" title={r.bottle_name ?? ""}>
                        {r.bottle_name || "—"}
                      </div>
                      {r.brand_name && (
                        <div className="text-muted-foreground">{r.brand_name}</div>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground font-mono">
                      {r.whiskybase_id ? `WB${r.whiskybase_id}` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted-foreground">
                      {r.client_ask_price != null ? formatPrice(r.client_ask_price, "EUR") : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-medium text-foreground">
                      {formatPrice(r.wb_avg_retail_price_eur, "EUR")}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted-foreground">
                      {formatPrice(r.wb_avg_retail_price, r.wb_avg_retail_currency)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted-foreground">
                      {formatPrice(r.wb_lowest_price_eur, "EUR")}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted-foreground">
                      {formatPrice(r.wb_highest_price_eur, "EUR")}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <PriceFlagBadge flag={r.price_flag} />
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted-foreground">
                      {r.wb_listing_count ?? "—"}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground align-top w-[280px] max-w-[280px]">
                      {listings.length === 0 ? (
                        "—"
                      ) : (
                        <div className="max-h-32 overflow-y-auto space-y-0.5 pr-1">
                          {listings.map((l, idx) => (
                            <div key={idx} className="flex items-baseline justify-between gap-2 leading-tight">
                              {l.url ? (
                                <a
                                  href={l.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-accent hover:underline truncate"
                                  title={l.shop}
                                >
                                  {l.shop || "View"}
                                </a>
                              ) : (
                                <span className="truncate" title={l.shop}>{l.shop || "—"}</span>
                              )}
                              <span className="font-mono text-foreground/80 shrink-0 tabular-nums text-right">
                                <span>{formatPrice(l.price, l.currency || r.wb_avg_retail_currency)}</span>
                                {l.price_eur != null && (l.currency || "EUR").toUpperCase() !== "EUR" && (
                                  <span className="block text-[0.65rem] text-muted-foreground">
                                    ≈ {formatPrice(l.price_eur, "EUR")}
                                  </span>
                                )}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <ScrapeStatusBadge status={r.wb_scrape_status} error={r.error_message} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PriceFlagBadge({ flag }: { flag: BottleResult["price_flag"] }) {
  if (!flag || flag === "no_wb_price" || flag === "no_client_price") {
    return <span className="text-zinc-600">—</span>;
  }
  const cfg = {
    wb_higher: { cls: "bg-green-950 text-green-400 border-green-900", label: "WB ↑" },
    wb_lower:  { cls: "bg-red-950 text-red-400 border-red-900", label: "WB ↓" },
    same:      { cls: "bg-yellow-950 text-yellow-400 border-yellow-900", label: "≈" },
  }[flag];
  if (!cfg) return <span className="text-zinc-600">—</span>;
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded border text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

function ScrapeStatusBadge({
  status,
  error,
}: {
  status: BottleResult["wb_scrape_status"];
  error: string | null;
}) {
  const cfg = {
    success: "bg-green-950 text-green-400 border-green-900",
    failed: "bg-red-950 text-red-400 border-red-900",
    skipped_no_id: "bg-zinc-900 text-zinc-500 border-zinc-800",
  }[status];

  const label = {
    success: "success",
    failed: "failed",
    skipped_no_id: "no wb id",
  }[status];

  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded border text-xs font-medium ${cfg}`}
      title={error ?? undefined}
    >
      {label}
    </span>
  );
}
