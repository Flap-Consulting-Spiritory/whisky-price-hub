"""
In-memory SSE event queue registry.
Each job gets an asyncio.Queue. The blocking scraper thread pushes events
using run_coroutine_threadsafe; the FastAPI SSE endpoint reads from the queue.
"""
import asyncio
import json
from typing import Optional

_queues: dict[str, asyncio.Queue] = {}
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the running event loop reference at FastAPI startup."""
    global _event_loop
    _event_loop = loop


def create_queue(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[job_id] = q
    return q


def get_queue(job_id: str) -> Optional[asyncio.Queue]:
    return _queues.get(job_id)


def remove_queue(job_id: str) -> None:
    _queues.pop(job_id, None)


def emit(job_id: str, event: dict) -> None:
    """
    Thread-safe: push an SSE event from the blocking scraper thread
    into the asyncio queue on the main event loop.
    """
    queue = get_queue(job_id)
    if queue is None or _event_loop is None:
        return
    asyncio.run_coroutine_threadsafe(queue.put(event), _event_loop)
