class ScrapeBanException(Exception):
    """Raised when WhiskyBase shows a Cloudflare captcha — safe to retry."""
    pass


class ScrapeHardBanException(Exception):
    """Raised on HTTP 403/429 — hard IP block, do not retry."""
    pass
