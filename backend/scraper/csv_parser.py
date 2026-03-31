"""
CSV parser for Spiritory KPI reports.
Normalizes WhiskyBase IDs and preserves all original columns for enriched output.
"""
import csv
import re
from typing import Optional


def extract_wb_id(raw: str) -> Optional[str]:
    """
    Normalize WhiskyBase ID to numeric string only.
    Handles: 'WB66259', ' WB272705' (leading space), 'WB272705 ' (trailing), empty.
    """
    numeric = re.sub(r'[^0-9]', '', (raw or '').strip())
    return numeric if numeric else None


def parse_csv(file_path: str) -> list[dict]:
    """
    Parse the Spiritory KPI CSV.

    Returns a list of bottle dicts with normalized fields.
    Each dict includes 'original_row' with all original columns preserved
    for writing the enriched output CSV later.
    """
    bottles = []
    with open(file_path, newline='', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Support both column name variants
            raw_wb_id = row.get('whiskybaseID') or row.get('wb_id') or row.get('whiskybase_id') or ''
            wb_id = extract_wb_id(raw_wb_id)

            raw_ask = (row.get('lowest_active_ask_price_now') or '').strip()
            client_ask_price: Optional[float] = None
            if raw_ask:
                try:
                    client_ask_price = float(re.sub(r'[^\d.]', '', raw_ask))
                except ValueError:
                    pass

            bottles.append({
                'row_index': i,
                'bottle_id': (row.get('bottle_id') or '').strip(),
                'whiskybase_id': wb_id,
                'bottle_name': (row.get('bottle_name') or '').strip(),
                'brand_name': (row.get('brand_name') or '').strip(),
                'client_ask_price': client_ask_price,
                'original_row': dict(row),  # preserve ALL original columns
            })

    return bottles


def write_enriched_csv(
    output_path: str,
    bottles: list[dict],  # parsed bottle dicts from parse_csv
    results: list[dict],  # bottle_results rows from DB ordered by row_index
) -> None:
    """
    Merge original CSV rows with scraped price data and write enriched output.
    New columns appended: wb_avg_retail_price, wb_avg_retail_currency,
    wb_lowest_price, wb_highest_price, wb_listing_count, wb_top_listings,
    wb_scrape_status, wb_scraped_at.
    """
    new_columns = [
        'wb_avg_retail_price',
        'wb_avg_retail_currency',
        'wb_lowest_price',
        'wb_highest_price',
        'wb_listing_count',
        'wb_top_listings',
        'wb_scrape_status',
        'wb_scraped_at',
        'price_flag',
    ]

    if not bottles:
        return

    # Build result lookup by row_index
    result_by_row: dict[int, dict] = {r['row_index']: r for r in results}

    # Determine original fieldnames from first bottle
    original_fieldnames = list(bottles[0]['original_row'].keys())
    all_fieldnames = original_fieldnames + new_columns

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
        writer.writeheader()

        for bottle in sorted(bottles, key=lambda b: b['row_index']):
            row = dict(bottle['original_row'])
            result = result_by_row.get(bottle['row_index'], {})

            row['wb_avg_retail_price'] = result.get('wb_avg_retail_price', '')
            row['wb_avg_retail_currency'] = result.get('wb_avg_retail_currency', '')
            row['wb_lowest_price'] = result.get('wb_lowest_price', '')
            row['wb_highest_price'] = result.get('wb_highest_price', '')
            row['wb_listing_count'] = result.get('wb_listing_count', '')
            row['wb_top_listings'] = result.get('wb_top_listings', '')
            row['wb_scrape_status'] = result.get('wb_scrape_status', 'skipped_no_id')
            row['wb_scraped_at'] = result.get('wb_scraped_at', '')
            row['price_flag'] = result.get('price_flag', '')

            writer.writerow(row)
