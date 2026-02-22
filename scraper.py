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

from bs4 import BeautifulSoup

SPA_MARKERS = ['id="root"', 'id="app"', 'id="__next"', 'id="__nuxt"']
MIN_TEXT_LENGTH = 200
PLAYWRIGHT_TIMEOUT = 30000  # ms


def needs_js_rendering(html: str) -> bool:
    """Detect if a page likely needs JavaScript rendering."""
    # Check for SPA markers
    for marker in SPA_MARKERS:
        if marker in html:
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(strip=True)
            if len(text) < MIN_TEXT_LENGTH:
                return True

    # Check if visible text is too short
    soup = BeautifulSoup(html, "lxml")
    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(strip=True)
    return len(text) < MIN_TEXT_LENGTH


def fetch_html_with_playwright(url: str) -> tuple[str | None, str | None]:
    """Fetch HTML using Playwright for JS-rendered pages. Returns (html, error)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html, None
    except Exception as e:
        return None, f"Playwright error: {e}"
