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
