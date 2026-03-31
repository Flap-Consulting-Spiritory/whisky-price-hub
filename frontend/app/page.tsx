import { UploadZone } from "@/components/upload-zone";
import { JobsTable } from "@/components/jobs-table";

export default function Home() {
  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Price Enrichment</h1>
        <p className="text-muted-foreground text-sm">
          Upload your Spiritory KPI CSV to automatically scrape WhiskyBase prices for every bottle with a WB ID.
        </p>
      </div>

      {/* Upload */}
      <section className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">New Job</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            CSV must include a <code className="text-accent">whiskybaseID</code> column
          </p>
        </div>
        <UploadZone />
      </section>

      {/* Job History */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">Job History</h2>
        <JobsTable />
      </section>
    </div>
  );
}
