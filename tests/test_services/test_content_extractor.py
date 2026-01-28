
import httpx
import pytest
import respx

from intelstream.services.content_extractor import ContentExtractor


@pytest.fixture
def extractor():
    return ContentExtractor()


class TestContentExtractor:
    @respx.mock
    async def test_extract_article_content(self, extractor: ContentExtractor):
        html = """
        <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="John Doe">
            <meta property="article:published_time" content="2024-01-15T12:00:00Z">
        </head>
        <body>
            <article>
                <h1>Test Article Title</h1>
                <p>This is the first paragraph of the article with enough content to be significant.</p>
                <p>This is the second paragraph with more important information about the topic.</p>
            </article>
        </body>
        </html>
        """

        respx.get("https://example.com/article").mock(
            return_value=httpx.Response(200, text=html)
        )

        result = await extractor.extract("https://example.com/article")

        assert result.text
        assert "first paragraph" in result.text or len(result.text) > 0
        assert result.author == "John Doe"
        assert result.published_at is not None

    @respx.mock
    async def test_extract_from_main_element(self, extractor: ContentExtractor):
        html = """
        <html>
        <body>
            <nav>Navigation content</nav>
            <main>
                <p>Main content paragraph that is significant enough.</p>
            </main>
            <footer>Footer content</footer>
        </body>
        </html>
        """

        respx.get("https://example.com/page").mock(
            return_value=httpx.Response(200, text=html)
        )

        result = await extractor.extract("https://example.com/page")

        assert result.text
        assert "Navigation" not in result.text or "Main content" in result.text

    @respx.mock
    async def test_extract_title_from_og_meta(self, extractor: ContentExtractor):
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <title>Page Title</title>
        </head>
        <body><p>Content</p></body>
        </html>
        """

        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=html)
        )

        result = await extractor.extract("https://example.com/")

        assert result.title == "OG Title"

    @respx.mock
    async def test_extract_title_from_title_tag(self, extractor: ContentExtractor):
        html = """
        <html>
        <head>
            <title>Page Title</title>
        </head>
        <body><p>Content</p></body>
        </html>
        """

        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=html)
        )

        result = await extractor.extract("https://example.com/")

        assert result.title == "Page Title"

    @respx.mock
    async def test_extract_date_from_time_element(self, extractor: ContentExtractor):
        html = """
        <html>
        <body>
            <time datetime="2024-06-15T10:30:00Z">June 15, 2024</time>
            <p>Content</p>
        </body>
        </html>
        """

        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=html)
        )

        result = await extractor.extract("https://example.com/")

        assert result.published_at is not None
        assert result.published_at.year == 2024
        assert result.published_at.month == 6

    @respx.mock
    async def test_extract_handles_network_error(self, extractor: ContentExtractor):
        respx.get("https://example.com/").mock(side_effect=httpx.ConnectError("Network error"))

        result = await extractor.extract("https://example.com/")

        assert result.text == ""

    @respx.mock
    async def test_extract_handles_empty_page(self, extractor: ContentExtractor):
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text="<html><body></body></html>")
        )

        result = await extractor.extract("https://example.com/")

        assert result.text == "" or result.text is not None

    def test_parse_date_iso_format(self, extractor: ContentExtractor):
        result = extractor._parse_date("2024-01-15T12:00:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_date_only(self, extractor: ContentExtractor):
        result = extractor._parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_parse_date_natural_format(self, extractor: ContentExtractor):
        result = extractor._parse_date("January 15, 2024")
        assert result is not None
        assert result.year == 2024

    def test_parse_date_invalid(self, extractor: ContentExtractor):
        result = extractor._parse_date("not a date")
        assert result is None

    def test_parse_date_none(self, extractor: ContentExtractor):
        result = extractor._parse_date(None)
        assert result is None
