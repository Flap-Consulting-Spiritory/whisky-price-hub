"""
WhiskyBase bottle page scraper.
Orchestrates browser, price parsing, and listing extraction.
"""
import random
import re
import time

from bs4 import BeautifulSoup
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from scraper.browser_manager import _get_context, close_session  # noqa: F401 (re-exported)
from scraper.price_parser import _parse_price, _parse_currency, _extract_prices_from_ld_json
from scraper.listing_extractor import _extract_listings
from scraper.exceptions import ScrapeBanException, ScrapeHardBanException


@retry(
    wait=wait_exponential(multiplier=2, min=30, max=180),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(ScrapeBanException),
    reraise=True,
)
def scrape_bottle_prices(whiskybase_id: str) -> dict:
    """
    Scrapes price data from a WhiskyBase bottle page.

    Returns:
        {
            "avg_retail_price": float | None,
            "avg_retail_currency": str,
            "lowest_price": float | None,
            "highest_price": float | None,
            "listing_count": int,
            "top_listings": [{"shop": str, "price": float, "currency": str, "url": str}],
        }
    """
    numeric_id = re.sub(r'[^0-9]', '', whiskybase_id)
    url = f"https://www.whiskybase.com/whiskies/whisky/{numeric_id}"

    data: dict = {
        "avg_retail_price": None,
        "avg_retail_currency": "EUR",
        "lowest_price": None,
        "highest_price": None,
        "listing_count": 0,
        "top_listings": [],
    }

    try:
        context = _get_context()
        page = context.new_page()

        response = page.goto(url, wait_until="domcontentloaded", timeout=45000)

        if response and response.status in [403, 429]:
            page.close()
            raise ScrapeHardBanException(f"Blocked by WhiskyBase! Status: {response.status}")

        # Human-like interaction
        time.sleep(random.uniform(1.5, 3.5))
        page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
        time.sleep(random.uniform(0.8, 2.0))

        # Scroll further to trigger lazy-loaded listings
        page.evaluate(f"window.scrollBy(0, {random.randint(400, 800)})")
        time.sleep(random.uniform(0.5, 1.5))

        html = page.content()
        page.close()

        # Cloudflare detection
        if any(marker in html for marker in (
            "Just a moment...",
            "cf-browser-verification",
            "cf-turnstile",
            "challenge-platform",
        )):
            raise ScrapeBanException("Cloudflare challenge detected!")

        soup = BeautifulSoup(html, 'html.parser')

        # ── 1. Try schema.org LD+JSON first ──────────────────────────────────
        ld_data = _extract_prices_from_ld_json(soup)
        if ld_data.get('prices'):
            prices = ld_data['prices']
            data['avg_retail_price'] = sum(prices) / len(prices)
            data['avg_retail_currency'] = ld_data.get('currency', 'EUR')
            data['lowest_price'] = min(prices)
            data['highest_price'] = max(prices)

        # ── 2. Average retail price from page stats ───────────────────────────
        avg_price_candidates = [
            soup.select_one('.whisky-price'),
            soup.select_one('.avg-price'),
            soup.select_one('[data-price]'),
            soup.select_one('.price-value'),
            soup.select_one('.whisky-stats .price'),
            soup.select_one('.wb-stats .price'),
        ]
        for el in avg_price_candidates:
            if el:
                raw = el.get('data-price') or el.get_text(strip=True)
                parsed = _parse_price(raw)
                if parsed and parsed > 0:
                    data['avg_retail_price'] = parsed
                    data['avg_retail_currency'] = _parse_currency(el.get_text())
                    break

        # Fallback: look for price near "average" / "retail" text
        if data['avg_retail_price'] is None:
            for elem in soup.find_all(['div', 'span', 'td', 'p']):
                text = elem.get_text(strip=True).lower()
                if any(kw in text for kw in ('average', 'avg', 'retail price', 'market price')):
                    for candidate in [elem, *elem.find_all(['span', 'strong', 'b'])]:
                        parsed = _parse_price(candidate.get_text(strip=True))
                        if parsed and 1 < parsed < 100000:
                            data['avg_retail_price'] = parsed
                            data['avg_retail_currency'] = _parse_currency(elem.get_text())
                            break
                    if data['avg_retail_price']:
                        break

        # ── 3. Individual listings ─────────────────────────────────────────────
        listing_prices, listings_found = _extract_listings(soup)

        if listing_prices:
            data['listing_count'] = len(listing_prices)
            data['top_listings'] = listings_found
            data['lowest_price'] = min(listing_prices)
            data['highest_price'] = max(listing_prices)
            if data['avg_retail_price'] is None:
                data['avg_retail_price'] = round(sum(listing_prices) / len(listing_prices), 2)
            data['avg_retail_currency'] = listings_found[0]['currency'] if listings_found else 'EUR'

        # ── 4. Listing count from page text ───────────────────────────────────
        if data['listing_count'] == 0:
            for pattern in [r'(\d+)\s+offer', r'(\d+)\s+listing', r'(\d+)\s+shop']:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    data['listing_count'] = int(match.group(1))
                    break

    except ScrapeHardBanException:
        raise

    except ScrapeBanException as e:
        print(f"    [Anti-Ban] Request blocked for {url}: {e} - Retrying...")
        raise

    except Exception as e:
        print(f"[WhiskyBase] Unhandled Error scraping {url}: {e}")
        raise e

    return data
