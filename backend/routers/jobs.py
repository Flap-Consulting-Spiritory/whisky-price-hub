"""
Job CRUD endpoints: create, list, get.
"""
import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from database import get_db, DB_PATH
from jobs_store import create_queue
from models import JobSummary, JobCreateResponse
from scraper.csv_parser import parse_csv
from scraper.job_runner import run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=1)  # patchright is process-scoped


def _row_to_summary(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "id": row["id"],
        "status": row["status"],
        "original_filename": row["original_filename"],
        "total_bottles": row["total_bottles"],
        "scraped": row["scraped"],
        "failed": row["failed"],
        "skipped": row["skipped"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "csv_output_path": row["csv_output_path"],
        "fx_rate_date": row["fx_rate_date"] if "fx_rate_date" in keys else None,
        "fx_fetched_at": row["fx_fetched_at"] if "fx_fetched_at" in keys else None,
        "fx_rates": row["fx_rates"] if "fx_rates" in keys else None,
    }


@router.post("", response_model=JobCreateResponse, status_code=201)
async def create_job(file: UploadFile = File(...)):
    """Upload a CSV file and start a scrape job."""
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Save uploaded CSV
    input_path = str(DATA_DIR / f"{job_id}_input.csv")
    async with aiofiles.open(input_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Parse to get bottle count
    try:
        bottles = parse_csv(input_path)
    except Exception as e:
        os.unlink(input_path)
        raise HTTPException(status_code=422, detail=f"Failed to parse CSV: {e}")

    total_bottles = len(bottles)

    # Save job to DB
    async for db in get_db():
        await db.execute("""
            INSERT INTO jobs (id, status, original_filename, total_bottles, created_at, csv_input_path)
            VALUES (?, 'pending', ?, ?, ?, ?)
        """, (job_id, file.filename, total_bottles, created_at, input_path))
        await db.commit()

    # Create SSE queue before starting thread
    create_queue(job_id)

    # Start scraping in background thread
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_executor, run_job, job_id)

    return {
        "job_id": job_id,
        "status": "pending",
        "total_bottles": total_bottles,
        "created_at": created_at,
    }


@router.get("", response_model=list[JobSummary])
async def list_jobs():
    """List all jobs ordered by creation date descending."""
    async for db in get_db():
        rows = await db.execute_fetchall(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        )
        return [_row_to_summary(r) for r in rows]


@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Return stored log lines for a job (for display on completed job pages)."""
    async for db in get_db():
        cursor = await db.execute(
            "SELECT ts, level, msg FROM job_logs WHERE job_id=? ORDER BY id",
            (job_id,)
        )
        rows = await cursor.fetchall()
        return [{"ts": r["ts"], "level": r["level"], "msg": r["msg"]} for r in rows]


@router.get("/{job_id}/progress")
async def get_job_progress(job_id: str):
    """Reconstruct chronological progress events from bottle_results.

    Mirrors the shape of live SSE 'progress' events so the frontend can replay
    the run's per-bottle outcomes after a page refresh. Only includes bottles
    that were actually scraped (excludes 'skipped_no_id' rows, since those
    never emitted a progress event live).
    """
    async for db in get_db():
        cursor = await db.execute(
            """
            SELECT whiskybase_id, bottle_name, wb_scrape_status,
                   wb_scraped_at, wb_avg_retail_price, wb_avg_retail_currency
            FROM bottle_results
            WHERE job_id = ?
              AND wb_scrape_status != 'skipped_no_id'
              AND wb_scraped_at IS NOT NULL
            ORDER BY id
            """,
            (job_id,),
        )
        rows = await cursor.fetchall()

    events = []
    scraped = 0
    failed = 0
    total = len(rows)
    for r in rows:
        status_db = r["wb_scrape_status"]
        if status_db in ("success",):
            scraped += 1
            status = "success"
        else:
            failed += 1
            status = "failed"
        ts_iso = r["wb_scraped_at"] or ""
        ts = ts_iso[11:19] if "T" in ts_iso else ts_iso[:8]
        events.append({
            "type": "progress",
            "ts": ts,
            "wb_id": r["whiskybase_id"],
            "bottle_name": r["bottle_name"],
            "status": status,
            "avg_price": r["wb_avg_retail_price"],
            "currency": r["wb_avg_retail_currency"],
            "scraped": scraped,
            "failed": failed,
            "total": total,
        })
    return events


@router.get("/{job_id}", response_model=JobSummary)
async def get_job(job_id: str):
    """Get a single job by ID."""
    async for db in get_db():
        cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return _row_to_summary(row)
