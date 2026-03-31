"""Pydantic models for API request/response validation."""
from pydantic import BaseModel
from typing import Optional


class JobSummary(BaseModel):
    id: str
    status: str
    original_filename: str
    total_bottles: int
    scraped: int
    failed: int
    skipped: int
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    csv_output_path: Optional[str] = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total_bottles: int
    created_at: str


class BottleResult(BaseModel):
    id: int
    job_id: str
    row_index: int
    bottle_id: Optional[str] = None
    whiskybase_id: Optional[str] = None
    bottle_name: Optional[str] = None
    brand_name: Optional[str] = None
    wb_avg_retail_price: Optional[float] = None
    wb_avg_retail_currency: Optional[str] = None
    wb_lowest_price: Optional[float] = None
    wb_highest_price: Optional[float] = None
    wb_listing_count: Optional[int] = None
    wb_top_listings: Optional[str] = None
    wb_scrape_status: str
    wb_scraped_at: Optional[str] = None
    error_message: Optional[str] = None
    client_ask_price: Optional[float] = None
    price_flag: Optional[str] = None


class ResultsResponse(BaseModel):
    total: int
    items: list[BottleResult]
