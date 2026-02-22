"""Content scraper — extracts raw article text from web URLs."""

import re
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Check if a URL has a valid HTTP/HTTPS scheme and netloc."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def url_to_slug(url: str) -> str:
    """Convert a URL to a filesystem-safe slug."""
    parsed = urlparse(url)
    # Remove scheme and www prefix
    raw = parsed.netloc.removeprefix("www.") + parsed.path
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate to 100 chars
    slug = slug[:100].rstrip("-")
    return slug.lower()

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 15


def fetch_html(url: str) -> tuple[str | None, str | None]:
    """Fetch HTML from a URL. Returns (html, error)."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.text, None
    except Exception as e:
        return None, str(e)
