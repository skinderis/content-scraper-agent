# Content Scraper Design

## Overview

A CLI Python script that extracts raw article text from web URLs using a multi-method fallback chain. Designed to be invoked by an AI agent.

## CLI Interface

```
python scraper.py --category <name> URL [URL ...]
python scraper.py --category <name> --file urls.txt
```

- `--category` (required): Subfolder name under `output/` (e.g., `seo`, `tech`, `fishing`)
- URLs: One or more URLs as positional args, or via `--file` with one URL per line
- Output: `./output/<category>/<url-slug>.txt`

## Architecture

Single-file script (`scraper.py`) with clean functions. Dependencies in `requirements.txt`.

### Extraction Pipeline

For each URL, sequentially:

1. **Fetch HTML** via `requests.get()` with realistic User-Agent, 15s timeout
2. **JS detection** — if visible text in HTML < 200 chars or contains SPA markers (`<div id="root"></div>`, `<div id="app"></div>`), re-fetch with Playwright (30s timeout)
3. **Extract text** using fallback chain:
   - `trafilatura.extract()` — primary, best article quality
   - `newspaper4k` `Article.parse()` — first fallback
   - Custom BeautifulSoup extractor (strip scripts/styles/nav, extract text) — last resort
4. **Validate** — text must be >= 50 chars, otherwise marked as failed

### URL Slug Generation

Strip protocol, replace non-alphanumeric chars with hyphens, truncate to reasonable length.

### Error Handling

- Timeouts: 15s HTTP, 30s Playwright. Catch, log, mark failed.
- HTTP errors (403, 404, 5xx): Log status, mark failed, continue.
- Invalid URLs: Validate format upfront, skip invalid.
- Empty content: All 3 extractors empty = failed.

### Summary Output

Printed to stdout after processing:

```
=== Scraping Summary ===
SUCCESS: https://example.com/article  -> output/seo/example-com-article.txt  [trafilatura]
SUCCESS: https://other.com/post       -> output/seo/other-com-post.txt       [newspaper4k]
FAILED:  https://blocked.com/page     -> 403 Forbidden
```

## Processing

Sequential — one URL at a time with a small delay between requests.

## Dependencies

- `trafilatura` — primary extractor
- `newspaper4k` — fallback extractor
- `beautifulsoup4` + `lxml` — last-resort extractor
- `requests` — HTTP fetching
- `playwright` — JS rendering (lazy import, only when needed)
