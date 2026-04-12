# CLAUDE.md

**Repository:** `https://github.com/Flap-Consulting-Spiritory/whisky-price-hub`

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Project Does

WhiskyPriceHub enriches a client's whisky inventory CSV (from Spiritory) with real-time retail prices scraped from WhiskyBase. Users upload a CSV, the backend scrapes each bottle's WB page, computes a price comparison flag, and produces a downloadable enriched CSV. Progress is streamed live via SSE.

---

## Running Locally

### Backend

The backend **must** run inside the Spirit/Scraper venv because `patchright` is only installed there. Port 8000 is typically occupied by another project; use 8001.

```bash
cd /home/john/Desktop/Projects/Spirit/WhiskyPriceHub/backend
source /home/john/Desktop/Projects/Spirit/Scraper/venv/bin/activate
uvicorn main:app --reload --port 8001
```

Install missing packages into that venv if needed:
```bash
pip install python-multipart aiofiles aiosqlite
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev
```

### Production URLs

- Backend: `https://api-whiskyhub.mentour.lat`
- Frontend: `https://whiskyhub.mentour.lat`
- Deployed via Coolify — push to `main` triggers redeploy automatically.

---

## Architecture

### Request Flow

```
Browser → Next.js API route (proxy) → FastAPI backend → SQLite
                                              ↓
                                    ThreadPoolExecutor
                                              ↓
                                    Patchright (Chromium)
                                              ↓
                                    WhiskyBase page scrape
                                              ↓
                                    SSE queue → EventSource → Browser
```

### Why the Proxy Layer

All frontend API routes (`frontend/app/api/**`) are thin Next.js proxies to the FastAPI backend. The `INTERNAL_API_URL` env var is used server-side (container-to-container), while `NEXT_PUBLIC_API_URL` is the public URL used client-side for SSE (EventSource doesn't go through the proxy).

### Thread Safety — The Critical Pattern

`patchright` (Playwright) is synchronous and blocking. It runs in a `ThreadPoolExecutor` (single worker — see `routers/jobs.py`). The scraper emits SSE events back to the async FastAPI event loop using:

```python
asyncio.run_coroutine_threadsafe(queue.put(event), loop)
```

`jobs_store.py` holds the global asyncio loop reference (set at startup) and per-job asyncio queues. Breaking this pattern causes silent SSE failures.

### CSV Format Expected

The input CSV comes from Spiritory's KPI report. Key columns:
- `whiskybase_id` or `whiskybase_url` — WB ID extracted via regex (numeric only; handles `WB66259`, ` WB272705`, `https://whiskybase.com/whiskies/66259` formats)
- `lowest_active_ask_price_now` — client's ask price; `0.00` means ask is inactive (`ask_active_now=False`), treated as no price (not zero)
- `bottle_id`, `bottle_name`, `brand_name`

### Price Flag Logic

`_compute_price_flag()` in `scraper/job_runner.py`:
- `wb_higher` — WB avg > client ask by >1%
- `wb_lower` — WB avg < client ask by >1%
- `same` — within 1%
- `no_wb_price` — WB returned no avg price (no listings or scrape failed)
- `no_client_price` — `client_ask` is `None` or `0.0` (inactive ask)

**Critical**: `if not client_ask:` catches both `None` and `0.0` to avoid ZeroDivisionError. Do not change to `if client_ask is None:`.

### WB Scraping Strategy (page_scraper.py)

Falls through multiple extraction strategies in order:
1. Schema.org LD+JSON structured data
2. CSS selectors for avg retail price block
3. Full-text keyword search ("average", "retail")
4. Individual listing DOM extraction + manual average computation

Cloudflare bans: `ScrapeBanException` (soft, retryable with cooldown) vs `ScrapeHardBanException` (HTTP 403/429, stops immediately). The outer retry loop in `job_runner.py` handles cooldowns of 10→20→40→60 min (up to 6 attempts). Each bottle also gets 3 generic-error retries before being marked failed.

### Log Persistence

`job_logs` table stores every SSE `log`-type event written during a run. The `GET /api/jobs/{id}/logs` endpoint serves this for completed jobs. `progress-feed.tsx` checks `isCompleted` prop: if true, fetches historical logs instead of opening SSE.

---

## Database Schema (SQLite)

Three tables in `data/whiskyprices.db`:

- **`jobs`** — one row per CSV upload (status, counts, timestamps, file paths)
- **`bottle_results`** — one row per bottle per job (all scraped prices, price_flag, error_message)
- **`job_logs`** — append-only log stream per job (ts, level, msg)

Migrations are handled in `database.py` with `try/except` on `ALTER TABLE` (SQLite has no `ADD COLUMN IF NOT EXISTS`).

---

## Deployment Notes

- No GitHub Actions CI — Coolify hooks directly on `git push origin main`
- Backend Dockerfile installs Chromium via `patchright install chromium`
- `data/` directory must be a persistent volume in Coolify (contains SQLite DB + CSV files)
- `PROXY_URL` env var enables residential proxy for Cloudflare bypass (optional)
- Stale job recovery: on startup, any job in `running`/`pending` state is marked `failed` (handles server restart mid-job)
