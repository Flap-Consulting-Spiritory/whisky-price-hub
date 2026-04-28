"""
EUR FX rate fetcher using ECB rates via frankfurter.app (no API key needed).
Fetched once per scraping job; the same rates are applied to every bottle in
the run so cross-bottle averages stay consistent.
"""
import json
import urllib.request
from datetime import datetime, timezone

FX_API_URL = "https://api.frankfurter.app/latest"
SUPPORTED_CURRENCIES = ("GBP", "USD", "CHF")


def fetch_eur_rates(currencies=SUPPORTED_CURRENCIES, timeout: float = 10.0) -> dict:
    """Fetch ECB rates and return a snapshot to be cached for the run.

    Returns:
        {
            "date": "2026-04-25",         # ECB rate date
            "fetched_at": "...",          # when we hit the API (ISO UTC)
            "rates_to_eur": {             # how many EUR for 1 unit of the key
                "EUR": 1.0,
                "GBP": 1.176,
                "USD": 0.93,
                "CHF": 1.05,
            },
        }

    On network failure raises an exception — caller decides whether to abort
    the job or proceed without conversion.
    """
    url = f"{FX_API_URL}?from=EUR&to={','.join(currencies)}"
    req = urllib.request.Request(url, headers={"User-Agent": "WhiskyPriceHub/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    eur_to_x = data.get("rates", {})
    rates_to_eur = {"EUR": 1.0}
    for cur in currencies:
        rate = eur_to_x.get(cur)
        if rate and rate > 0:
            rates_to_eur[cur] = round(1.0 / rate, 6)

    return {
        "date": data.get("date", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "rates_to_eur": rates_to_eur,
    }


def to_eur(amount, currency: str, rates_to_eur: dict):
    """Convert `amount` in `currency` to EUR using the snapshot.

    Returns None if amount is None or currency is unknown.
    """
    if amount is None or currency is None:
        return None
    rate = rates_to_eur.get(currency.upper())
    if rate is None:
        return None
    return round(float(amount) * rate, 2)
