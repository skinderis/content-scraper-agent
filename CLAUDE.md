# CLAUDE.md — Content Scraper Agent Instructions

## Role

`scraper.py` is a subprocess tool. Call it to fetch raw article text from URLs. It handles HTTP fetching, JS rendering detection, and extraction. You consume its output files downstream.

## Invocation

Always invoke as a subprocess from the project root with the venv Python:

```bash
.venv/bin/python scraper.py --category <category> <url> [<url> ...]
```

Or with a file of URLs:

```bash
.venv/bin/python scraper.py --category <category> --file <path/to/urls.txt>
```

### Category

Choose a category that describes the content domain (e.g. `seo`, `tech`, `finance`, `health`). This becomes the output subfolder. Use lowercase, no spaces.

### Many URLs

If you have more than ~5 URLs, write them to a temp file and use `--file`:

```bash
# Write URLs to a temp file
echo "https://a.com/article
https://b.com/post" > /tmp/urls.txt

# Run scraper
.venv/bin/python scraper.py --category tech --file /tmp/urls.txt
```

## Reading Output

### stdout

Parse stdout to determine success/failure per URL:

- Lines starting with `SUCCESS:` — scrape succeeded
- Lines starting with `FAILED:` — scrape failed, reason follows `->`

Example:
```
SUCCESS: https://example.com/article  -> output/seo/example-com-article.txt  [trafilatura]
FAILED:  https://blocked.com/page     -> 403 Forbidden
```

The summary block at the end gives totals:
```
Total: 3 | Success: 2 | Failed: 1
```

### Output files

Successful results are saved to `output/<category>/<url-slug>.txt`. The file contains clean article text only — read it directly for downstream use.

```python
with open("output/seo/example-com-article.txt") as f:
    article_text = f.read()
```

## Error Handling

| Error | Action |
|-------|--------|
| `403 Forbidden` | Skip — the site is blocking scrapers. Do not retry. |
| `404 Not Found` | Skip — URL is invalid or content removed. |
| `Timeout` | May retry once. If it fails again, skip. |
| `Playwright error` | JS rendering failed. Treat as failed scrape. |
| `All extraction methods returned empty content` | Page has no extractable article text (e.g. login wall, empty page). Skip. |

## Constraints

- Scraping is **sequential** — one URL at a time with a 1-second delay between requests
- Do **not** invoke multiple scraper processes in parallel for the same category
- Do **not** pass invalid or non-HTTP(S) URLs — validate before calling
- Output files are **overwritten** if the same URL is scraped again

## Workflow Example

```
1. Receive list of article URLs to process
2. Group URLs by category
3. For each category, invoke scraper.py with that group
4. Parse stdout to identify successes and failures
5. Read output/<category>/*.txt files for article content
6. Continue pipeline with extracted text
```
