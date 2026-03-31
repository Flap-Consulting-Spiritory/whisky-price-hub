export interface Job {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  original_filename: string;
  total_bottles: number;
  scraped: number;
  failed: number;
  skipped: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  csv_input_path: string;
  csv_output_path: string | null;
}

export interface TopListing {
  shop: string;
  price: number;
  currency: string;
  url: string;
}

export interface BottleResult {
  id: number;
  job_id: string;
  row_index: number;
  bottle_id: string | null;
  whiskybase_id: string | null;
  bottle_name: string | null;
  brand_name: string | null;
  wb_avg_retail_price: number | null;
  wb_avg_retail_currency: string | null;
  wb_lowest_price: number | null;
  wb_highest_price: number | null;
  wb_listing_count: number | null;
  wb_top_listings: string | null;
  wb_scrape_status: "success" | "failed" | "skipped_no_id";
  wb_scraped_at: string | null;
  error_message: string | null;
}

export interface ResultsResponse {
  total: number;
  items: BottleResult[];
}

export type SSEEventType = "progress" | "log" | "done" | "ping";

export interface SSEProgressEvent {
  type: "progress";
  bottle_name: string;
  wb_id: string;
  status: "success" | "failed" | "skipped_no_id";
  scraped: number;
  total: number;
  ts: string;
}

export interface SSELogEvent {
  type: "log";
  level: "info" | "warn" | "error";
  msg: string;
  ts: string;
}

export interface SSEDoneEvent {
  type: "done";
  status: "completed" | "failed";
  scraped: number;
  failed: number;
  skipped: number;
}

export type SSEEvent = SSEProgressEvent | SSELogEvent | SSEDoneEvent;
