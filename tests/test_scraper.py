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
