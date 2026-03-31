"""
Results and download endpoints.
GET /api/jobs/{job_id}/results  — paginated bottle results
GET /api/jobs/{job_id}/download — enriched CSV file download
"""
import os

import aiofiles
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import get_db
from models import BottleResult, ResultsResponse

router = APIRouter(prefix="/api/jobs", tags=["results"])


def _row_to_result(row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "row_index": row["row_index"],
        "bottle_id": row["bottle_id"],
        "whiskybase_id": row["whiskybase_id"],
        "bottle_name": row["bottle_name"],
        "brand_name": row["brand_name"],
        "wb_avg_retail_price": row["wb_avg_retail_price"],
        "wb_avg_retail_currency": row["wb_avg_retail_currency"],
        "wb_lowest_price": row["wb_lowest_price"],
        "wb_highest_price": row["wb_highest_price"],
        "wb_listing_count": row["wb_listing_count"],
        "wb_top_listings": row["wb_top_listings"],
        "wb_scrape_status": row["wb_scrape_status"],
        "wb_scraped_at": row["wb_scraped_at"],
        "error_message": row["error_message"],
        "client_ask_price": row["client_ask_price"],
        "price_flag": row["price_flag"],
    }


@router.get("/{job_id}/results", response_model=ResultsResponse)
async def get_results(
    job_id: str,
    status: str | None = Query(None, description="Filter by scrape status"),
):
    """Get all bottle results for a job, optionally filtered by status."""
    async for db in get_db():
        # Verify job exists
        cursor = await db.execute("SELECT id FROM jobs WHERE id=?", (job_id,))
        job = await cursor.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if status:
            rows = await db.execute_fetchall(
                "SELECT * FROM bottle_results WHERE job_id=? AND wb_scrape_status=? ORDER BY row_index",
                (job_id, status)
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM bottle_results WHERE job_id=? ORDER BY row_index",
                (job_id,)
            )

        items = [_row_to_result(r) for r in rows]
        return {"total": len(items), "items": items}


@router.get("/{job_id}/download")
async def download_csv(job_id: str):
    """Download the enriched CSV. Only available when job is completed."""
    async for db in get_db():
        cur = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] == "running" or row["status"] == "pending":
            raise HTTPException(status_code=409, detail="Job is still running")
        if not row["csv_output_path"] or not os.path.exists(row["csv_output_path"]):
            raise HTTPException(status_code=404, detail="Output CSV not available")

        output_path = row["csv_output_path"]
        original_name = row["original_filename"].replace('.csv', '')
        download_name = f"enriched_{original_name}.csv"

        async def file_streamer():
            async with aiofiles.open(output_path, 'rb') as f:
                while chunk := await f.read(65536):
                    yield chunk

        return StreamingResponse(
            file_streamer(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
        )
