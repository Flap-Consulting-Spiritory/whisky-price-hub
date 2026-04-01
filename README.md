# WhiskyPriceHub

Enriches a Spiritory whisky inventory CSV with real-time retail prices scraped from WhiskyBase. Upload a CSV, the backend scrapes each bottle's WhiskyBase page, computes a price comparison flag, and produces a downloadable enriched CSV. Progress is streamed live via SSE.

## Requirements

- VPS running Ubuntu 22.04 or later (2 vCPU / 2 GB RAM minimum)
- Docker 24+ with the Compose plugin
- Ports 3000 (frontend) and 8000 (backend) open in your firewall

## Production Setup

**1. Install Docker**

```bash
curl -fsSL https://get.docker.com | sh
```

**2. Clone the repository**

```bash
git clone https://github.com/AlejandroTechFlap/WhiskyPriceHub.git
cd WhiskyPriceHub
```

**3. Configure environment variables**

```bash
cp .env.example .env
nano .env
```

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Public URL of the backend, e.g. `https://api.yourdomain.com` or `http://YOUR_IP:8000` |
| `ALLOWED_ORIGINS` | Yes | Frontend origin allowed by CORS, e.g. `https://yourdomain.com` |
| `AUTH_USERNAME` | Yes | Login username for the frontend |
| `AUTH_PASSWORD` | Yes | Login password for the frontend |
| `PROXY_URL` | No | Residential proxy to reduce Cloudflare bans: `http://user:pass@ip:port` |

**4. Create the data directory**

```bash
mkdir -p data
```

**5. Build and start**

```bash
docker compose up -d --build
```

First run takes ~5 minutes — installs Chromium inside the backend container.

- Frontend: `http://YOUR_SERVER_IP:3000`
- Backend API docs: `http://YOUR_SERVER_IP:8000/docs`

## Maintenance

Update to the latest version:

```bash
git pull
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f
docker compose logs -f backend
```

Stop / restart:

```bash
docker compose down
docker compose restart
```

## Architecture

```
Browser -> Next.js (port 3000) -> FastAPI (port 8000) -> SQLite
                                         |
                                ThreadPoolExecutor
                                         |
                               Patchright (Chromium)
                                         |
                               WhiskyBase page scrape
                                         |
                               SSE queue -> EventSource -> Browser
```

The frontend proxies all API calls server-side using `INTERNAL_API_URL=http://backend:8000` (container-to-container). The browser uses `NEXT_PUBLIC_API_URL` only for SSE connections, which cannot go through the proxy.

SQLite database and uploaded CSV files are stored in the `data/` directory, which is mounted as a volume and persists across container rebuilds.

## Input CSV Format

The input CSV must come from Spiritory's KPI report. Required columns:

- `whiskybase_id` or `whiskybase_url` — WB identifier (handles `WB66259`, `WB272705`, or full URL formats)
- `lowest_active_ask_price_now` — client's ask price; `0.00` means the ask is inactive
- `bottle_id`, `bottle_name`, `brand_name`

## Price Flags

Each bottle in the enriched CSV gets a `price_flag`:

| Flag | Meaning |
|---|---|
| `wb_higher` | WhiskyBase avg > client ask by more than 1% |
| `wb_lower` | WhiskyBase avg < client ask by more than 1% |
| `same` | Within 1% of each other |
| `no_wb_price` | WhiskyBase returned no average price |
| `no_client_price` | Client ask is inactive or missing |
