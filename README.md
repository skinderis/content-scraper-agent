# Content Scraper

Extracts raw article text from web URLs and saves it as `.txt` files.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

Scrape one or more URLs directly:

```bash
python scraper.py --category seo https://example.com/article https://other.com/post
```

Scrape from a file (one URL per line):

```bash
python scraper.py --category tech --file urls.txt
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--category` | Yes | Output subfolder name (e.g. `seo`, `tech`, `fishing`) |
| `urls` | No* | One or more URLs as positional arguments |
| `--file` | No* | Path to a text file with one URL per line |

*At least one of `urls` or `--file` must be provided.

## Output

Files are saved to `output/<category>/<url-slug>.txt`:

```
output/
  seo/
    example-com-article.txt
    other-com-post.txt
```

Each file contains clean article text — no HTML, no scripts, no navigation.

## Extraction Pipeline

For each URL:

1. Fetch HTML via `requests` with a realistic browser User-Agent (15s timeout)
2. Detect JS-rendered pages — if visible text < 200 chars or SPA markers found, re-fetch with Playwright (30s timeout)
3. Extract text using a fallback chain:
   - **trafilatura** — primary, best article quality
   - **newspaper4k** — first fallback
   - **BeautifulSoup** — last resort (strips scripts, styles, nav)
4. Save result to `output/<category>/` or mark as failed

## Summary Output

Printed to stdout after all URLs are processed:

```
=== Scraping Summary ===
SUCCESS: https://example.com/article  -> output/seo/example-com-article.txt  [trafilatura]
FAILED:  https://blocked.com/page     -> 403 Forbidden

Total: 2 | Success: 1 | Failed: 1
```

## Running Tests

```bash
pip install pytest
pytest tests/test_scraper.py -v
```
