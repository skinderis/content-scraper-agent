# X/Twitter Tweet Scraping Support

## Problem

The scraper reports SUCCESS on X/Twitter URLs but only extracts the "JavaScript is disabled" fallback page. X.com requires JS and blocks headless browsers, so the normal fetch+extract pipeline fails.

## Solution

Detect X/Twitter tweet URLs and route them to dedicated extraction using two unauthenticated APIs: FxTwitter (primary) and Twitter oEmbed (fallback).

## URL Detection

Match tweet URLs with pattern: `(x.com|twitter.com)/USER/status/ID`

Extract the username and tweet ID from the path.

## Tweet Extraction Pipeline

Bypasses the normal HTML fetch+extract pipeline entirely.

### Primary: FxTwitter API

- Endpoint: `GET https://api.fxtwitter.com/{user}/status/{id}`
- Returns: JSON with `tweet.text`, author info, metrics
- No authentication required
- Third-party service (risk: could go offline)

### Fallback: Twitter oEmbed

- Endpoint: `GET https://publish.twitter.com/oembed?url={tweet_url}`
- Returns: JSON with `html` field containing `<blockquote>` with tweet text
- Parse `<p>` tags from the blockquote to extract clean text
- Officially supported by Twitter, most stable long-term

## Integration

In `scrape_url()`, before the HTML fetch step:

```python
if is_twitter_url(url):
    return scrape_tweet(url)
```

The `scrape_tweet()` function returns the same dict format as `scrape_url()` (`url`, `text`, `method`, `success`, `error`).

## Output

Same format as all other scrapes: `output/<category>/<slug>.txt` containing the tweet text. The `method` field reports `fxtwitter` or `oembed`.

## Error Handling

- FxTwitter 404 or network error -> try oEmbed
- FxTwitter 401 (private tweet) -> try oEmbed
- Both fail -> mark failed with descriptive error
- Network timeouts -> same 15s timeout as other requests

## Dependencies

None new. Uses `requests` and `beautifulsoup4` (both already installed).
