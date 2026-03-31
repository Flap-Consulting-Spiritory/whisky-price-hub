"""
Patchright browser session management.
Shared singleton context with periodic refresh for anti-bot evasion.
"""
import os
import random

from patchright.sync_api import sync_playwright, BrowserContext

PROXY_URL = os.environ.get("PROXY_URL", None)

_CONTEXT_REFRESH_EVERY = 10

_session: dict = {
    "playwright": None,
    "browser": None,
    "context": None,
    "requests_count": 0,
}

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
]


def _get_context() -> BrowserContext:
    """Return (or create) the shared browser context. Refreshes every N requests."""
    if (
        _session["context"] is not None
        and _session["requests_count"] > 0
        and _session["requests_count"] % _CONTEXT_REFRESH_EVERY == 0
    ):
        print(f"    [Anti-Ban] Refreshing browser context after {_session['requests_count']} requests...")
        close_session()

    if _session["context"] is None:
        _session["playwright"] = sync_playwright().start()

        launch_kwargs: dict = {
            "headless": True,
            "channel": "chromium",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        if PROXY_URL:
            launch_kwargs["proxy"] = {"server": PROXY_URL}

        _session["browser"] = _session["playwright"].chromium.launch(**launch_kwargs)
        _session["context"] = _session["browser"].new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            viewport=random.choice(_VIEWPORTS),
            device_scale_factor=1,
            has_touch=False,
            locale="en-US",
            timezone_id="America/New_York",
        )

    _session["requests_count"] += 1
    return _session["context"]


def close_session():
    """Closes the shared browser session safely."""
    try:
        if _session["browser"]:
            try:
                _session["browser"].close()
            except Exception as e:
                print(f"[WhiskyBase] Error closing browser: {e}")
    finally:
        try:
            if _session["playwright"]:
                _session["playwright"].stop()
        except Exception as e:
            print(f"[WhiskyBase] Error stopping playwright: {e}")
        finally:
            _session["browser"] = None
            _session["context"] = None
            _session["playwright"] = None
            _session["requests_count"] = 0
