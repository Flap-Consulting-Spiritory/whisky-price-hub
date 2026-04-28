"""
WhiskyPriceHub FastAPI application.
"""
import asyncio
import logging
import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("whiskyhub")

import jobs_store
from database import init_db
from routers import jobs, stream, results

app = FastAPI(title="WhiskyPriceHub API", version="1.0.0")

_ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(stream.router)
app.include_router(results.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s: %s\n%s",
        request.method, request.url.path,
        exc, traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.on_event("startup")
async def startup():
    await init_db()
    loop = asyncio.get_running_loop()
    jobs_store.set_loop(loop)
    print("[WhiskyPriceHub] Database initialized. Event loop stored.")
    # Recover stale jobs: any job still 'running' or 'pending' at startup was
    # interrupted by a server restart — mark them as failed and reconcile the
    # failed counter so it equals total - scraped - skipped (otherwise the UI
    # shows "Failed" with failed=0, which is confusing).
    from database import get_db
    async for db in get_db():
        cursor = await db.execute(
            "SELECT id, total_bottles, scraped, skipped FROM jobs "
            "WHERE status IN ('running', 'pending')"
        )
        stale = await cursor.fetchall()
        for row in stale:
            interrupted = max(0, (row["total_bottles"] or 0) - (row["scraped"] or 0) - (row["skipped"] or 0))
            await db.execute(
                "UPDATE jobs SET status='failed', finished_at=datetime('now'), failed=? "
                "WHERE id=?",
                (interrupted, row["id"]),
            )
        await db.commit()
    print(f"[WhiskyPriceHub] Stale running/pending jobs marked failed ({len(stale)}).")


@app.get("/health")
async def health():
    return {"status": "ok"}
