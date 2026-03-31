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


@app.get("/health")
async def health():
    return {"status": "ok"}
