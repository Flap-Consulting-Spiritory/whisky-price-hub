"""
DOM listing extraction for WhiskyBase bottle pages.
Finds retailer listings and extracts price, shop name, and URL.
"""
import re

from bs4 import BeautifulSoup

from scraper.price_parser import _parse_price, _parse_currency

_LISTING_SELECTORS = [
    '.listing',
    '.offer',
    '.wb--listing',
    'tr.offer-row',
    '.shop-listing',
    '.retailer-listing',
    '[data-listing]',
    '.price-listing',
]


def _extract_listings(soup: BeautifulSoup) -> tuple[list[float], list[dict]]:
    """
    Find all retailer listing elements in page and extract price/shop/url data.

    Returns:
        (listing_prices, listings_found) where listing_prices is a list of floats
        and listings_found is a list of dicts with keys: shop, price, currency, url.
    """
    listing_elements = []
    for sel in _LISTING_SELECTORS:
        elements = soup.select(sel)
        if elements:
            listing_elements = elements
            break

    # Fallback: look for table rows with price data
    if not listing_elements:
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) > 1:
                sample_text = table.get_text()
                if any(sym in sample_text for sym in ('€', '$', '£', 'EUR', 'USD', 'GBP')):
                    listing_elements = rows[1:]  # skip header row
                    break

    listing_prices: list[float] = []
    listings_found: list[dict] = []

    # Realistic per-bottle whisky range. €15000 covers all but the most extreme
    # collectibles and blocks placeholder/scam listings (e.g. €99999) and
    # accidental order-of-magnitude typos.
    PRICE_MIN = 10.0
    PRICE_MAX = 15000.0

    for elem in listing_elements:
        elem_text = elem.get_text(separator=' ', strip=True)

        # Collect ALL price candidates in this listing element, then pick the
        # smallest one within the realistic range. This handles shops that
        # display both the bottle price AND a per-liter price (pro 1 l, /L, …)
        # — the per-liter price is always larger for <1L bottles, so taking
        # the minimum reliably yields the bottle price.
        candidates: list[float] = []

        for price_sel in ['.price', '.listing-price', '[data-price]', '.amount', 'strong', 'b']:
            price_elem = (
                elem.select_one(price_sel)
                if price_sel.startswith('.') or price_sel.startswith('[')
                else elem.find(price_sel)
            )
            if price_elem:
                parsed = _parse_price(price_elem.get_text(strip=True))
                if parsed and PRICE_MIN <= parsed <= PRICE_MAX:
                    candidates.append(parsed)

        # Always also scan free text — many WhiskyBase listings render the
        # price as plain text without a dedicated class.
        for match in re.findall(r'[\€\$\£]?\s*(\d{1,5}[.,]\d{2})', elem_text):
            parsed = _parse_price(match)
            if parsed and PRICE_MIN <= parsed <= PRICE_MAX:
                candidates.append(parsed)

        price = min(candidates) if candidates else None

        # Extract shop name
        shop = ''
        for shop_sel in ['.shop-name', '.retailer-name', '.store-name', 'a.shop', '.merchant']:
            shop_elem = elem.select_one(shop_sel)
            if shop_elem:
                shop = shop_elem.get_text(strip=True)
                break
        if not shop:
            link = elem.find('a')
            if link:
                shop = link.get_text(strip=True) or (
                    link.get('href', '').split('/')[2] if link.get('href') else ''
                )

        # Extract URL
        listing_url = ''
        link_elem = elem.find('a', href=True)
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('http'):
                listing_url = href
            elif href.startswith('/'):
                listing_url = f"https://www.whiskybase.com{href}"

        currency = _parse_currency(elem_text)

        if price:
            listing_prices.append(price)
            listings_found.append({
                "shop": shop[:100],
                "price": price,
                "currency": currency,
                "url": listing_url[:500],
            })

    return listing_prices, listings_found
