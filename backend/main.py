"""
WhiskyPriceHub FastAPI application.
"""
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.on_event("startup")
async def startup():
    await init_db()
    loop = asyncio.get_running_loop()
    jobs_store.set_loop(loop)
    print("[WhiskyPriceHub] Database initialized. Event loop stored.")


@app.get("/health")
async def health():
    return {"status": "ok"}
