"""Content scraper — extracts raw article text from web URLs."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


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

def is_twitter_url(url: str) -> bool:
    """Check if a URL is an X/Twitter tweet URL."""
    parsed = urlparse(url)
    if parsed.netloc not in ("x.com", "twitter.com", "www.x.com", "www.twitter.com"):
        return False
    parts = parsed.path.strip("/").split("/")
    return len(parts) >= 3 and parts[1] == "status"


def parse_tweet_url(url: str) -> tuple[str, str]:
    """Extract (username, tweet_id) from a tweet URL."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    return parts[0], parts[2]


import requests

FXTWITTER_API = "https://api.fxtwitter.com"
OEMBED_API = "https://publish.twitter.com/oembed"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 15


def fetch_tweet_fxtwitter(username: str, tweet_id: str) -> tuple[str | None, str | None]:
    """Fetch tweet text via FxTwitter API. Returns (text, error)."""
    try:
        url = f"{FXTWITTER_API}/{username}/status/{tweet_id}"
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        tweet = data.get("tweet", {})

        # Check for X Article (long-form content)
        article = tweet.get("article")
        if article:
            blocks = article.get("content", {}).get("blocks", [])
            title = article.get("title", "")
            parts = []
            if title:
                parts.append(title)
            for block in blocks:
                block_text = block.get("text", "")
                if block_text:
                    parts.append(block_text)
            text = "\n\n".join(parts)
            if text and len(text.strip()) > 0:
                return text.strip(), None

        # Regular tweet text
        text = tweet.get("text")
        if text and len(text.strip()) > 0:
            return text.strip(), None
        return None, "FxTwitter returned empty tweet text"
    except Exception as e:
        return None, str(e)


def fetch_tweet_oembed(tweet_url: str) -> tuple[str | None, str | None]:
    """Fetch tweet text via Twitter oEmbed API. Returns (text, error)."""
    try:
        response = requests.get(
            OEMBED_API,
            params={"url": tweet_url},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        html = data.get("html", "")
        soup = BeautifulSoup(html, "lxml")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs)
        if text and len(text.strip()) > 0:
            return text.strip(), None
        return None, "oEmbed returned empty tweet text"
    except Exception as e:
        return None, str(e)


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

import trafilatura
from newspaper import Article


def extract_with_trafilatura(html: str) -> str | None:
    """Extract article text using trafilatura."""
    try:
        text = trafilatura.extract(html)
        return text if text and len(text.strip()) >= 50 else None
    except Exception:
        return None


def extract_with_newspaper(html: str, url: str) -> str | None:
    """Extract article text using newspaper4k."""
    try:
        article = Article(url)
        article.set_html(html)
        article.parse()
        text = article.text
        return text if text and len(text.strip()) >= 50 else None
    except Exception:
        return None


def extract_with_beautifulsoup(html: str) -> str | None:
    """Extract article text using BeautifulSoup as last resort."""
    try:
        soup = BeautifulSoup(html, "lxml")
        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text if text and len(text.strip()) >= 10 else None
    except Exception:
        return None


def scrape_tweet(url: str) -> dict:
    """Scrape a tweet URL. Returns dict with url, text, method, success, error."""
    result = {"url": url, "text": None, "method": None, "success": False, "error": None}

    username, tweet_id = parse_tweet_url(url)

    # Try FxTwitter first
    text, error = fetch_tweet_fxtwitter(username, tweet_id)
    if text:
        result.update(text=text, method="fxtwitter", success=True)
        return result

    # Fall back to oEmbed
    text, oembed_error = fetch_tweet_oembed(url)
    if text:
        result.update(text=text, method="oembed", success=True)
        return result

    result["error"] = f"FxTwitter: {error}; oEmbed: {oembed_error}"
    return result


def scrape_url(url: str) -> dict:
    """Scrape a single URL. Returns dict with url, text, method, success, error."""
    # Route tweet URLs to dedicated handler
    if is_twitter_url(url):
        return scrape_tweet(url)

    result = {"url": url, "text": None, "method": None, "success": False, "error": None}

    # Fetch HTML
    html, error = fetch_html(url)
    if html is None:
        result["error"] = error
        return result

    # Check if JS rendering is needed
    if needs_js_rendering(html):
        js_html, js_error = fetch_html_with_playwright(url)
        if js_html:
            html = js_html

    # Try extraction methods in order
    text = extract_with_trafilatura(html)
    if text:
        result.update(text=text, method="trafilatura", success=True)
        return result

    text = extract_with_newspaper(html, url)
    if text:
        result.update(text=text, method="newspaper4k", success=True)
        return result

    text = extract_with_beautifulsoup(html)
    if text:
        result.update(text=text, method="beautifulsoup", success=True)
        return result

    result["error"] = "All extraction methods returned empty content"
    return result
import os

DEFAULT_OUTPUT_DIR = "output"


def save_result(result: dict, category: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> str | None:
    """Save successful result to a .txt file. Returns filepath or None."""
    if not result["success"]:
        return None

    category_dir = os.path.join(output_dir, category)
    os.makedirs(category_dir, exist_ok=True)

    slug = url_to_slug(result["url"])
    filepath = os.path.join(category_dir, f"{slug}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result["text"])

    return filepath


def print_summary(results: list[dict]) -> None:
    """Print a summary of scraping results."""
    print("\n=== Scraping Summary ===")
    for r in results:
        if r["success"]:
            print(f"SUCCESS: {r['url']}  -> {r.get('filepath', 'N/A')}  [{r['method']}]")
        else:
            print(f"FAILED:  {r['url']}  -> {r['error']}")

    total = len(results)
    succeeded = sum(1 for r in results if r["success"])
    print(f"\nTotal: {total} | Success: {succeeded} | Failed: {total - succeeded}")
import argparse
import time

DELAY_BETWEEN_REQUESTS = 1  # seconds


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape article text from web URLs."
    )
    parser.add_argument(
        "--category", required=True, help="Output subfolder name (e.g., seo, tech)"
    )
    parser.add_argument(
        "--file", help="Path to a file with one URL per line"
    )
    parser.add_argument(
        "urls", nargs="*", help="URLs to scrape"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)

    # Collect URLs
    urls = list(args.urls)
    if args.file:
        with open(args.file) as f:
            urls.extend(line.strip() for line in f if line.strip())

    if not urls:
        print("Error: No URLs provided.")
        return

    # Validate URLs
    valid_urls = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            print(f"Skipping invalid URL: {url}")

    if not valid_urls:
        print("Error: No valid URLs to process.")
        return

    # Process each URL
    results = []
    for i, url in enumerate(valid_urls):
        print(f"[{i + 1}/{len(valid_urls)}] Scraping: {url}")
        result = scrape_url(url)
        filepath = save_result(result, category=args.category)
        result["filepath"] = filepath
        results.append(result)

        if i < len(valid_urls) - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print_summary(results)


if __name__ == "__main__":
    main()
