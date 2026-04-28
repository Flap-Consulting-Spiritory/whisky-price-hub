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

### Production

- Public URL: `https://pricecheck.spiritory.info` (frontend only — backend is NOT exposed publicly)
- Server: Hetzner VPS, hostname `spiritory-ai`, IP `89.167.24.25`, SSH port `27`
- SSH alias (already configured in `~/.ssh/config`): **`ssh spiritory-vps`**
  - User: `flapagency` · Key: `~/.ssh/id_ed25519_spiritory_vps` (key auth, no password needed)
- Deploy path on server: `/home/flapagency/spiritory/whisky-price-hub/`
- Reverse proxy: **Nginx** (NOT Coolify) — vhost at `/etc/nginx/sites-enabled/pricecheck.spiritory.info`, TLS via Certbot/Let's Encrypt
- Containers (host-bound to loopback only):
  - `whisky-price-hub-frontend-1` → `127.0.0.1:3010 → 3000`
  - `whisky-price-hub-backend-1` → `127.0.0.1:8010 → 8000`
- Port mapping is forced via `docker-compose.override.yml` on the server (binds to `127.0.0.1` so only nginx can reach the containers).
- Production `.env` lives at `/home/flapagency/spiritory/whisky-price-hub/.env`. Current values: `NEXT_PUBLIC_API_URL=https://pricecheck.spiritory.info`, `ALLOWED_ORIGINS=https://pricecheck.spiritory.info` (same-origin — SSE goes via the Next.js proxy, not direct to backend).
- **No automatic deploy hook.** A `git push origin main` does NOT redeploy. To redeploy:
  ```bash
  ssh spiritory-vps
  cd /home/flapagency/spiritory/whisky-price-hub
  git pull
  docker compose up -d --build
  ```
  Rebuild the frontend whenever `NEXT_PUBLIC_API_URL` changes (it's baked in at build time).
- Nginx has a dedicated `location ~ ^/api/jobs/.+/stream$` block with `proxy_buffering off` for SSE. **It still proxies to the frontend container (`:3010`)**, so the Next.js route at `frontend/app/api/jobs/[id]/stream/route.ts` is in the path — that proxy can buffer and is the most likely culprit for SSE "connecting…" symptoms.
- Useful one-liners:
  ```bash
  ssh spiritory-vps "docker logs --tail=200 whisky-price-hub-backend-1"
  ssh spiritory-vps "docker logs --tail=200 whisky-price-hub-frontend-1"
  ssh spiritory-vps "sudo nginx -t && sudo systemctl reload nginx"
  ```

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

All frontend API routes (`frontend/app/api/**`) are thin Next.js proxies to the FastAPI backend. `INTERNAL_API_URL` is used server-side (container-to-container, e.g. `http://backend:8000`); `NEXT_PUBLIC_API_URL` is the public URL baked into the client bundle.

`getStreamUrl()` in `frontend/lib/api.ts` points the EventSource at `${NEXT_PUBLIC_API_URL}/api/jobs/{id}/stream`. In production this is the **same origin** as the frontend (`https://pricecheck.spiritory.info`), so SSE goes: browser → nginx → Next.js (`:3010`) → Next.js proxy route → FastAPI (`:8010`). The backend is not reachable cross-origin, so CORS is not the failure mode in production — buffering at the Next.js proxy hop is.

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
- `wb_higher` — WB avg strictly greater than client ask
- `wb_lower` — WB avg strictly less than client ask
- `same` — WB avg exactly equal to client ask (floats; rare in practice since avgs are computed)
- `no_wb_price` — WB returned no avg price (no listings or scrape failed)
- `no_client_price` — `client_ask` is `None` or `0.0` (inactive ask)

The comparison is **absolute** — there is no tolerance band. The previous ±1% band was dropped because the client wants to flag any price gap red/green even when small (per-bottle business decision).

**Critical**: `if not client_ask:` catches both `None` and `0.0` (no active ask). Do not change to `if client_ask is None:`.

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

- No GitHub Actions CI and **no auto-deploy** — `git push` does not redeploy. Manual `git pull && docker compose up -d --build` on the VPS is required (see Production section above for the SSH alias and path).
- Backend Dockerfile installs Chromium via `patchright install chromium`
- `data/` directory is a host-mounted volume on the VPS (`./data` in the compose file → contains SQLite DB + CSV files); never delete it
- `PROXY_URL` env var enables residential proxy for Cloudflare bypass (optional)
- Stale job recovery: on startup, any job in `running`/`pending` state is marked `failed` (handles server restart mid-job)
