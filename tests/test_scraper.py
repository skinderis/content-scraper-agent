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
