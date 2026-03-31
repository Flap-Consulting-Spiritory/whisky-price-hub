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


@router.get("/{job_id}", response_model=JobSummary)
async def get_job(job_id: str):
    """Get a single job by ID."""
    async for db in get_db():
        cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return _row_to_summary(row)
