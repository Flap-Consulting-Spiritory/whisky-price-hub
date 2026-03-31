"""
SQLite database initialization and helpers using aiosqlite.
"""
import aiosqlite
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "data" / "whiskyprices.db"))


async def init_db() -> None:
    """Create tables if they don't exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id                TEXT PRIMARY KEY,
                status            TEXT NOT NULL DEFAULT 'pending',
                original_filename TEXT NOT NULL,
                total_bottles     INTEGER NOT NULL DEFAULT 0,
                scraped           INTEGER NOT NULL DEFAULT 0,
                failed            INTEGER NOT NULL DEFAULT 0,
                skipped           INTEGER NOT NULL DEFAULT 0,
                created_at        TEXT NOT NULL,
                started_at        TEXT,
                finished_at       TEXT,
                csv_input_path    TEXT NOT NULL,
                csv_output_path   TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bottle_results (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id                 TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                row_index              INTEGER NOT NULL,
                bottle_id              TEXT,
                whiskybase_id          TEXT,
                bottle_name            TEXT,
                brand_name             TEXT,
                wb_avg_retail_price    REAL,
                wb_avg_retail_currency TEXT,
                wb_lowest_price        REAL,
                wb_highest_price       REAL,
                wb_listing_count       INTEGER,
                wb_top_listings        TEXT,
                wb_scrape_status       TEXT NOT NULL,
                wb_scraped_at          TEXT,
                error_message          TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bottle_results_job_id
            ON bottle_results(job_id)
        """)
        await db.commit()


async def get_db():
    """Async context manager for a database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
