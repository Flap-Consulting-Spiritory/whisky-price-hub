"""
SSE streaming endpoint: GET /api/jobs/{job_id}/stream
Streams real-time scraping progress events to the browser.
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import get_db
from jobs_store import get_queue

router = APIRouter(prefix="/api/jobs", tags=["stream"])


async def _event_generator(job_id: str):
    """Yield SSE-formatted events from the job's asyncio queue."""
    queue = get_queue(job_id)

    if queue is None:
        # Job may already be finished — send a done event with current DB state
        async for db in get_db():
            cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
            row = await cursor.fetchone()
            if row:
                yield f"data: {json.dumps({'type': 'done', 'status': row['status'], 'scraped': row['scraped'], 'failed': row['failed'], 'skipped': row['skipped']})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'done', 'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=15.0)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
        except asyncio.TimeoutError:
            # Keepalive ping
            yield "event: ping\ndata: {}\n\n"
        except Exception:
            break


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE endpoint — streams real-time scraping events for a job."""
    # Verify job exists
    async for db in get_db():
        cursor = await db.execute("SELECT id, status FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

    return StreamingResponse(
        _event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
