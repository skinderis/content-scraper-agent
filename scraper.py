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
