"""
Job orchestration loop.
Runs in a ThreadPoolExecutor (patchright is sync).
Emits SSE events via jobs_store.emit() using asyncio.run_coroutine_threadsafe.
Mirrors the proven run_scraper() pattern from Scraper/scraper_engine.py.
"""
import aiosqlite
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scraper.exceptions import ScrapeBanException, ScrapeHardBanException
from scraper.page_scraper import scrape_bottle_prices
from scraper.browser_manager import close_session
from scraper.csv_parser import parse_csv, write_enriched_csv
from utils.jitter import random_delay
from database import DB_PATH
from jobs_store import emit, remove_queue

from tenacity import RetryError as TenacityRetryError

# Mirrored from scraper_engine.py
BAN_COOLDOWNS = [600, 1200, 2400, 3600]  # 10, 20, 40, 60 minutes
MAX_BAN_RETRIES = 6

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_sync():
    """Return a synchronous sqlite3 connection (used inside the blocking thread)."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_job(job_id: str) -> None:
    """
    Blocking function — run in a ThreadPoolExecutor.
    Reads job from DB, processes each bottle, emits SSE events.
    """
    def _emit(type_: str, **kwargs):
        event = {
            "type": type_,
            "ts": datetime.now().strftime("%H:%M:%S"),
            **kwargs,
        }
        print(f"[Job {job_id[:8]}] {event}")
        emit(job_id, event)

    conn = _db_sync()
    try:
        # Mark job as running
        conn.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=?",
            (_now_iso(), job_id)
        )
        conn.commit()

        # Load job metadata
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            _emit("done", status="failed", msg="Job not found")
            return

        csv_input_path = row["csv_input_path"]
        original_filename = row["original_filename"]

        _emit("log", level="info", msg=f"[Job] Starting: {original_filename}")

        # Parse CSV
        bottles = parse_csv(csv_input_path)
        total = len(bottles)
        conn.execute("UPDATE jobs SET total_bottles=? WHERE id=?", (total, job_id))
        conn.commit()

        _emit("log", level="info", msg=f"[Job] {total} rows loaded from CSV")

        # Count skipped (no WB ID) upfront
        to_scrape = [b for b in bottles if b['whiskybase_id']]
        to_skip = [b for b in bottles if not b['whiskybase_id']]

        _emit("log", level="info", msg=f"[Job] {len(to_scrape)} bottles with WB ID, {len(to_skip)} skipped (no ID)")

        # Insert skipped rows immediately
        for bottle in to_skip:
            _emit("log", level="warn",
                  msg=f"  → Skipped: {bottle['bottle_name'] or bottle['bottle_id']} — no WhiskyBase ID in CSV")
            conn.execute("""
                INSERT INTO bottle_results
                (job_id, row_index, bottle_id, whiskybase_id, bottle_name, brand_name,
                 wb_scrape_status, wb_scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, 'skipped_no_id', ?)
            """, (
                job_id, bottle['row_index'], bottle['bottle_id'],
                None, bottle['bottle_name'], bottle['brand_name'], _now_iso()
            ))
        conn.execute("UPDATE jobs SET skipped=? WHERE id=?", (len(to_skip), job_id))
        conn.commit()

        scraped_count = 0
        failed_count = 0
        ban_retries = 0
        processed_idx = 0

        while processed_idx < len(to_scrape):
            hit_ban = False

            for i in range(processed_idx, len(to_scrape)):
                bottle = to_scrape[i]
                wb_id = bottle['whiskybase_id']
                bottle_name = bottle['bottle_name'] or f"Bottle {bottle['bottle_id']}"

                _emit("log", level="info",
                      msg=f"  → Processing [{i+1}/{len(to_scrape)}] {bottle_name} (WB: {wb_id})")

                try:
                    random_delay(8.0, 15.0)

                    _emit("log", level="info", msg=f"  → Scraping WhiskyBase...")

                    price_data = scrape_bottle_prices(wb_id, emit_fn=_emit)

                    # Save to DB
                    conn.execute("""
                        INSERT INTO bottle_results
                        (job_id, row_index, bottle_id, whiskybase_id, bottle_name, brand_name,
                         wb_avg_retail_price, wb_avg_retail_currency,
                         wb_lowest_price, wb_highest_price, wb_listing_count, wb_top_listings,
                         wb_scrape_status, wb_scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', ?)
                    """, (
                        job_id,
                        bottle['row_index'],
                        bottle['bottle_id'],
                        wb_id,
                        bottle['bottle_name'],
                        bottle['brand_name'],
                        price_data.get('avg_retail_price'),
                        price_data.get('avg_retail_currency', 'EUR'),
                        price_data.get('lowest_price'),
                        price_data.get('highest_price'),
                        price_data.get('listing_count', 0),
                        json.dumps(price_data.get('top_listings', [])),
                        _now_iso(),
                    ))
                    scraped_count += 1
                    conn.execute(
                        "UPDATE jobs SET scraped=? WHERE id=?",
                        (scraped_count, job_id)
                    )
                    _emit("log", level="info",
                          msg=(
                              f"  → Saved: avg={price_data.get('avg_retail_price')} "
                              f"{price_data.get('avg_retail_currency', 'EUR')}, "
                              f"low={price_data.get('lowest_price')}, "
                              f"high={price_data.get('highest_price')}, "
                              f"listings={price_data.get('listing_count', 0)}"
                          ))
                    conn.commit()

                    ban_retries = 0
                    processed_idx = i + 1

                    _emit("progress",
                          bottle_name=bottle_name,
                          wb_id=wb_id,
                          status="success",
                          avg_price=price_data.get('avg_retail_price'),
                          currency=price_data.get('avg_retail_currency', 'EUR'),
                          listing_count=price_data.get('listing_count', 0),
                          scraped=scraped_count,
                          failed=failed_count,
                          total=len(to_scrape))

                except (ScrapeBanException, ScrapeHardBanException, TenacityRetryError) as e:
                    ban_retries += 1
                    close_session()

                    if ban_retries > MAX_BAN_RETRIES:
                        _emit("log", level="error",
                              msg=f"[FATAL] Banned {MAX_BAN_RETRIES} times. Stopping.")
                        hit_ban = False  # exit outer loop too
                        processed_idx = len(to_scrape)  # mark all remaining as done
                        # Save remaining as failed
                        for remaining_bottle in to_scrape[i:]:
                            conn.execute("""
                                INSERT OR IGNORE INTO bottle_results
                                (job_id, row_index, bottle_id, whiskybase_id, bottle_name, brand_name,
                                 wb_scrape_status, wb_scraped_at, error_message)
                                VALUES (?, ?, ?, ?, ?, ?, 'failed', ?, ?)
                            """, (
                                job_id, remaining_bottle['row_index'],
                                remaining_bottle['bottle_id'], remaining_bottle['whiskybase_id'],
                                remaining_bottle['bottle_name'], remaining_bottle['brand_name'],
                                _now_iso(), "Max ban retries reached"
                            ))
                            failed_count += 1
                        conn.execute("UPDATE jobs SET failed=? WHERE id=?", (failed_count, job_id))
                        conn.commit()
                        break

                    cooldown = BAN_COOLDOWNS[min(ban_retries - 1, len(BAN_COOLDOWNS) - 1)]
                    _emit("log", level="warning",
                          msg=f"[BAN] Cloudflare detected. Waiting {cooldown // 60} min before retry ({ban_retries}/{MAX_BAN_RETRIES})...")

                    # Don't block event loop — sleep in thread is fine
                    time.sleep(cooldown)

                    _emit("log", level="info", msg="[BAN] Cooldown complete. Resuming...")
                    hit_ban = True
                    processed_idx = i  # retry from this bottle
                    break

                except Exception as e:
                    _emit("log", level="error",
                          msg=f"  → Error on {bottle_name}: {e}")

                    conn.execute("""
                        INSERT OR IGNORE INTO bottle_results
                        (job_id, row_index, bottle_id, whiskybase_id, bottle_name, brand_name,
                         wb_scrape_status, wb_scraped_at, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, 'failed', ?, ?)
                    """, (
                        job_id, bottle['row_index'], bottle['bottle_id'], wb_id,
                        bottle['bottle_name'], bottle['brand_name'],
                        _now_iso(), str(e)[:500]
                    ))
                    failed_count += 1
                    conn.execute("UPDATE jobs SET failed=? WHERE id=?", (failed_count, job_id))
                    conn.commit()

                    processed_idx = i + 1

                    _emit("progress",
                          bottle_name=bottle_name,
                          wb_id=wb_id,
                          status="failed",
                          scraped=scraped_count,
                          failed=failed_count,
                          total=len(to_scrape))

            if not hit_ban:
                break

        # ── Write enriched CSV ────────────────────────────────────────────────
        output_filename = f"{job_id}_enriched.csv"
        output_path = str(DATA_DIR / output_filename)

        try:
            all_results = conn.execute(
                "SELECT * FROM bottle_results WHERE job_id=? ORDER BY row_index",
                (job_id,)
            ).fetchall()
            results_dicts = [dict(r) for r in all_results]

            write_enriched_csv(output_path, bottles, results_dicts)
            _emit("log", level="info", msg=f"[Job] Enriched CSV written: {output_filename}")
        except Exception as e:
            _emit("log", level="error", msg=f"[Job] Failed to write CSV: {e}")
            output_path = None

        # ── Finalize job ──────────────────────────────────────────────────────
        conn.execute("""
            UPDATE jobs SET status='completed', finished_at=?, csv_output_path=?,
            scraped=?, failed=?
            WHERE id=?
        """, (_now_iso(), output_path, scraped_count, failed_count, job_id))
        conn.commit()

        close_session()

        _emit("done",
              status="completed",
              scraped=scraped_count,
              failed=failed_count,
              skipped=len(to_skip))

    except Exception as e:
        _emit("log", level="error", msg=f"[Job] Fatal error: {e}")
        conn.execute(
            "UPDATE jobs SET status='failed', finished_at=? WHERE id=?",
            (_now_iso(), job_id)
        )
        conn.commit()
        close_session()
        _emit("done", status="failed", msg=str(e))

    finally:
        conn.close()
        # Clean up SSE queue after a short delay to allow frontend to receive 'done'
        time.sleep(5)
        remove_queue(job_id)
