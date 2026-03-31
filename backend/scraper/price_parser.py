"""
Price and currency parsing utilities for WhiskyBase HTML.
Handles European and US number formats, LD+JSON schema.org data.
"""
import json
import re

from bs4 import BeautifulSoup


def _parse_price(text: str) -> float | None:
    """Extract float from text like '€ 89,50' or '$120.00' or '1.234,56'."""
    if not text:
        return None
    # Remove currency symbols and letters
    cleaned = re.sub(r'[^\d.,]', '', text.strip())
    if not cleaned:
        return None
    # Handle European thousands separator: "1.234,56" → "1234.56"
    if ',' in cleaned and '.' in cleaned:
        # Assume last separator is decimal
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # European: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Could be European decimal: "89,50"
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_currency(text: str) -> str:
    """Detect currency from surrounding text."""
    for sym, code in [('€', 'EUR'), ('$', 'USD'), ('£', 'GBP'), ('CHF', 'CHF')]:
        if sym in text or code in text:
            return code
    return 'EUR'  # WhiskyBase default (EU-based)


def _extract_prices_from_ld_json(soup: BeautifulSoup) -> dict:
    """Try schema.org Offer structured data first."""
    result = {}
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            # Handle list or single object
            items = data if isinstance(data, list) else [data]
            for item in items:
                offers = item.get('offers', [])
                if isinstance(offers, dict):
                    offers = [offers]
                prices = []
                currency = 'EUR'
                for offer in offers:
                    p = offer.get('price') or offer.get('lowPrice')
                    if p:
                        try:
                            prices.append(float(str(p).replace(',', '.')))
                        except (ValueError, TypeError):
                            pass
                    c = offer.get('priceCurrency')
                    if c:
                        currency = c
                if prices:
                    result['prices'] = prices
                    result['currency'] = currency
                    return result
        except Exception:
            continue
    return result
