# Content Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI Python script that extracts raw article text from URLs using trafilatura -> newspaper4k -> BeautifulSoup fallback chain, with automatic JS rendering detection.

**Architecture:** Single-file `scraper.py` with helper functions, invoked via CLI. Sequential URL processing. Output to `output/<category>/` as `.txt` files.

**Tech Stack:** Python 3.10+, trafilatura, newspaper4k, beautifulsoup4, lxml, requests, playwright

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `scraper.py` (empty placeholder)
- Create: `.gitignore`

**Step 1: Create requirements.txt**

```
trafilatura
newspaper4k
beautifulsoup4
lxml
requests
playwright
```

**Step 2: Create .gitignore**

```
output/
__pycache__/
*.pyc
.venv/
```

**Step 3: Create empty scraper.py placeholder**

```python
"""Content scraper — extracts raw article text from web URLs."""
```

**Step 4: Install dependencies**

Run: `pip install -r requirements.txt`

**Step 5: Install Playwright browsers**

Run: `playwright install chromium`

**Step 6: Commit**

```bash
git add requirements.txt scraper.py .gitignore
git commit -m "feat: project setup with dependencies"
```

---

### Task 2: URL Validation and Slug Generation

**Files:**
- Modify: `scraper.py`
- Create: `tests/test_scraper.py`

**Step 1: Write the failing tests**

```python
# tests/test_scraper.py
from scraper import validate_url, url_to_slug


def test_validate_url_valid():
    assert validate_url("https://example.com/article") is True


def test_validate_url_invalid():
    assert validate_url("not-a-url") is False


def test_validate_url_no_scheme():
    assert validate_url("example.com/article") is False


def test_url_to_slug_basic():
    assert url_to_slug("https://example.com/my-article") == "example-com-my-article"


def test_url_to_slug_strips_protocol():
    slug = url_to_slug("https://www.example.com/path")
    assert not slug.startswith("https")
    assert not slug.startswith("www")


def test_url_to_slug_truncates_long_urls():
    long_url = "https://example.com/" + "a" * 300
    slug = url_to_slug(long_url)
    assert len(slug) <= 100


def test_url_to_slug_no_trailing_hyphens():
    slug = url_to_slug("https://example.com/path/")
    assert not slug.endswith("-")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py -v`
Expected: FAIL — cannot import `validate_url`, `url_to_slug`

**Step 3: Implement validate_url and url_to_slug**

Add to `scraper.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add URL validation and slug generation"
```

---

### Task 3: HTML Fetching with User-Agent

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_scraper.py
from unittest.mock import patch, Mock
from scraper import fetch_html

def test_fetch_html_success():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Hello world</body></html>"
    mock_response.raise_for_status = Mock()

    with patch("scraper.requests.get", return_value=mock_response) as mock_get:
        html, error = fetch_html("https://example.com")
        assert html == "<html><body>Hello world</body></html>"
        assert error is None
        # Verify User-Agent is set
        call_kwargs = mock_get.call_args
        assert "User-Agent" in call_kwargs[1]["headers"]


def test_fetch_html_timeout():
    with patch("scraper.requests.get", side_effect=Exception("Timeout")):
        html, error = fetch_html("https://example.com")
        assert html is None
        assert "Timeout" in error


def test_fetch_html_403():
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.raise_for_status = Mock(
        side_effect=Exception("403 Client Error")
    )

    with patch("scraper.requests.get", return_value=mock_response):
        html, error = fetch_html("https://example.com")
        assert html is None
        assert "403" in error
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py::test_fetch_html_success -v`
Expected: FAIL — cannot import `fetch_html`

**Step 3: Implement fetch_html**

Add to `scraper.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k fetch`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add HTML fetching with User-Agent"
```

---

### Task 4: JS-Rendered Page Detection and Playwright Fetching

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_scraper.py
from scraper import needs_js_rendering, fetch_html_with_playwright


def test_needs_js_rendering_empty_body():
    html = "<html><body><div id='root'></div></body></html>"
    assert needs_js_rendering(html) is True


def test_needs_js_rendering_spa_marker():
    html = '<html><body><div id="app"></div></body></html>'
    assert needs_js_rendering(html) is True


def test_needs_js_rendering_normal_page():
    html = "<html><body><p>" + "Some article content. " * 50 + "</p></body></html>"
    assert needs_js_rendering(html) is False


def test_needs_js_rendering_short_text():
    html = "<html><body><p>Loading...</p></body></html>"
    assert needs_js_rendering(html) is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py -v -k needs_js`
Expected: FAIL — cannot import `needs_js_rendering`

**Step 3: Implement needs_js_rendering and fetch_html_with_playwright**

Add to `scraper.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k needs_js`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add JS rendering detection and Playwright fetching"
```

---

### Task 5: Extraction Methods (trafilatura, newspaper4k, BeautifulSoup)

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_scraper.py
from scraper import extract_with_trafilatura, extract_with_newspaper, extract_with_beautifulsoup

SAMPLE_HTML = """
<html>
<head><title>Test Article</title></head>
<body>
<nav>Navigation links here</nav>
<article>
<h1>Test Article Title</h1>
<p>This is the first paragraph of the article with enough content to be meaningful.
It discusses various topics and provides information that a reader would find useful.</p>
<p>This is the second paragraph continuing the article content with additional details
and explanations that expand on the initial topic presented above.</p>
</article>
<footer>Footer content here</footer>
</body>
</html>
"""


def test_extract_with_trafilatura():
    result = extract_with_trafilatura(SAMPLE_HTML)
    # trafilatura may return content or None depending on its heuristics
    # We just test it doesn't crash and returns str or None
    assert result is None or isinstance(result, str)


def test_extract_with_newspaper():
    result = extract_with_newspaper(SAMPLE_HTML, "https://example.com/test")
    assert result is None or isinstance(result, str)


def test_extract_with_beautifulsoup():
    result = extract_with_beautifulsoup(SAMPLE_HTML)
    assert isinstance(result, str)
    assert "Navigation links here" not in result or "article content" in result
    assert "<script" not in result
    assert "<style" not in result


def test_extract_with_beautifulsoup_strips_tags():
    html = """
    <html><body>
    <script>var x = 1;</script>
    <style>.foo { color: red; }</style>
    <nav>Skip this</nav>
    <p>Keep this paragraph content that is meaningful.</p>
    </body></html>
    """
    result = extract_with_beautifulsoup(html)
    assert "var x = 1" not in result
    assert ".foo" not in result
    assert "Keep this paragraph" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py -v -k extract`
Expected: FAIL — cannot import extraction functions

**Step 3: Implement the three extractors**

Add to `scraper.py`:

```python
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
        return text if text and len(text.strip()) >= 50 else None
    except Exception:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k extract`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add trafilatura, newspaper4k, and BeautifulSoup extractors"
```

---

### Task 6: Orchestrator — scrape_url Function

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_scraper.py
from scraper import scrape_url


def test_scrape_url_returns_result_dict():
    """Test that scrape_url returns expected structure with mocked fetch."""
    sample_html = "<html><body><article><p>" + "Article content here. " * 20 + "</p></article></body></html>"

    with patch("scraper.fetch_html", return_value=(sample_html, None)):
        result = scrape_url("https://example.com/article")
        assert "url" in result
        assert "text" in result
        assert "method" in result
        assert "success" in result
        assert result["success"] is True
        assert result["method"] in ("trafilatura", "newspaper4k", "beautifulsoup")


def test_scrape_url_fetch_failure():
    with patch("scraper.fetch_html", return_value=(None, "Connection timeout")):
        result = scrape_url("https://example.com/article")
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py::test_scrape_url_returns_result_dict -v`
Expected: FAIL — cannot import `scrape_url`

**Step 3: Implement scrape_url**

Add to `scraper.py`:

```python
def scrape_url(url: str) -> dict:
    """Scrape a single URL. Returns dict with url, text, method, success, error."""
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k scrape_url`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add scrape_url orchestrator with fallback chain"
```

---

### Task 7: File Output and Summary

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_scraper.py
import os
import tempfile
from scraper import save_result, print_summary


def test_save_result_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = {
            "url": "https://example.com/test-article",
            "text": "This is the article content that is long enough to be valid.",
            "method": "trafilatura",
            "success": True,
            "error": None,
        }
        filepath = save_result(result, category="seo", output_dir=tmpdir)
        assert os.path.exists(filepath)
        assert filepath.endswith(".txt")
        assert "/seo/" in filepath
        with open(filepath) as f:
            assert f.read() == result["text"]


def test_save_result_skips_failed():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = {
            "url": "https://example.com/fail",
            "text": None,
            "method": None,
            "success": False,
            "error": "403 Forbidden",
        }
        filepath = save_result(result, category="seo", output_dir=tmpdir)
        assert filepath is None


def test_print_summary(capsys):
    results = [
        {"url": "https://a.com", "success": True, "method": "trafilatura", "error": None, "filepath": "output/seo/a-com.txt"},
        {"url": "https://b.com", "success": False, "method": None, "error": "403 Forbidden", "filepath": None},
    ]
    print_summary(results)
    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "FAILED" in captured.out
    assert "trafilatura" in captured.out
    assert "403" in captured.out
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py -v -k "save_result or print_summary"`
Expected: FAIL — cannot import functions

**Step 3: Implement save_result and print_summary**

Add to `scraper.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k "save_result or print_summary"`
Expected: All PASS

**Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add file output and summary printing"
```

---

### Task 8: CLI Entry Point (argparse + main)

**Files:**
- Modify: `scraper.py`
- Modify: `tests/test_scraper.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_scraper.py
from scraper import parse_args


def test_parse_args_urls():
    args = parse_args(["--category", "seo", "https://a.com", "https://b.com"])
    assert args.category == "seo"
    assert args.urls == ["https://a.com", "https://b.com"]


def test_parse_args_file(tmp_path):
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\nhttps://b.com\n")
    args = parse_args(["--category", "tech", "--file", str(url_file)])
    assert args.category == "tech"
    assert args.file == str(url_file)


def test_parse_args_category_required():
    import pytest
    with pytest.raises(SystemExit):
        parse_args(["https://example.com"])
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scraper.py -v -k parse_args`
Expected: FAIL — cannot import `parse_args`

**Step 3: Implement parse_args and main**

Add to `scraper.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scraper.py -v -k parse_args`
Expected: All PASS

**Step 5: Run full test suite**

Run: `pytest tests/test_scraper.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add CLI entry point with argparse"
```

---

### Task 9: Integration Test — End-to-End Smoke Test

**Files:**
- Modify: `tests/test_scraper.py`

**Step 1: Write an integration test**

```python
# Add to tests/test_scraper.py
def test_main_end_to_end(tmp_path, capsys):
    """Integration test: run main with a mocked URL."""
    sample_html = "<html><body><article><p>" + "This is real article content. " * 20 + "</p></article></body></html>"

    with patch("scraper.fetch_html", return_value=(sample_html, None)):
        from scraper import main
        main(["--category", "test", "https://example.com/test-article"])

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "example-com-test-article" in captured.out

    # Verify file was created
    assert os.path.exists("output/test/example-com-test-article.txt")

    # Clean up
    import shutil
    shutil.rmtree("output/test", ignore_errors=True)
```

**Step 2: Run integration test**

Run: `pytest tests/test_scraper.py::test_main_end_to_end -v`
Expected: PASS

**Step 3: Run full test suite one final time**

Run: `pytest tests/test_scraper.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_scraper.py
git commit -m "test: add end-to-end integration test"
```

---

### Task 10: Manual Smoke Test with a Real URL

**Step 1: Run against a real article**

Run: `python scraper.py --category test https://en.wikipedia.org/wiki/Web_scraping`

Expected: SUCCESS, file created at `output/test/en-wikipedia-org-wiki-web-scraping.txt`

**Step 2: Verify output file has clean text**

Run: `head -20 output/test/en-wikipedia-org-wiki-web-scraping.txt`
Expected: Clean article text, no HTML tags, no CSS, no JavaScript.

**Step 3: Clean up test output**

Run: `rm -rf output/test`

**Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: adjustments from manual smoke test"
```
