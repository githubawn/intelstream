from datetime import UTC, datetime

import httpx
import pytest
import respx

from intelstream.adapters.rss import RSSAdapter

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Blog</title>
  <link href="https://testblog.com/"/>
  <updated>2024-01-15T12:00:00Z</updated>
  <entry>
    <title>Atom Article</title>
    <link href="https://testblog.com/atom-article"/>
    <id>https://testblog.com/atom-article</id>
    <updated>2024-01-15T12:00:00Z</updated>
    <author>
      <name>Atom Author</name>
    </author>
    <summary>This is an Atom feed entry.</summary>
  </entry>
</feed>
"""

SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test RSS Blog</title>
    <link>https://rssblog.com</link>
    <item>
      <title>RSS Article</title>
      <link>https://rssblog.com/rss-article</link>
      <guid>rss-article-123</guid>
      <pubDate>Tue, 16 Jan 2024 08:00:00 GMT</pubDate>
      <description>RSS article description.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_MULTIPLE_AUTHORS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Multi-Author Blog</title>
    <item>
      <title>Collaborative Article</title>
      <link>https://blog.com/collab</link>
      <guid>collab-123</guid>
      <pubDate>Wed, 17 Jan 2024 14:00:00 GMT</pubDate>
      <dc:creator>Author One</dc:creator>
      <dc:creator>Author Two</dc:creator>
    </item>
  </channel>
</rss>
"""


class TestRSSAdapter:
    async def test_get_feed_url_returns_identifier(self) -> None:
        adapter = RSSAdapter()
        url = await adapter.get_feed_url("https://example.com/feed.xml")
        assert url == "https://example.com/feed.xml"

    @respx.mock
    async def test_fetch_atom_feed(self) -> None:
        respx.get("https://testblog.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_ATOM_FEED)
        )

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)
            items = await adapter.fetch_latest("https://testblog.com/feed.xml")

        assert len(items) == 1
        item = items[0]
        assert item.title == "Atom Article"
        assert item.author == "Atom Author"
        assert item.original_url == "https://testblog.com/atom-article"
        assert item.published_at == datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    @respx.mock
    async def test_fetch_rss_feed(self) -> None:
        respx.get("https://rssblog.com/feed").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)
            items = await adapter.fetch_latest("https://rssblog.com/feed")

        assert len(items) == 1
        item = items[0]
        assert item.title == "RSS Article"
        assert item.external_id == "rss-article-123"
        assert item.author == "Test RSS Blog"
        assert item.published_at == datetime(2024, 1, 16, 8, 0, 0, tzinfo=UTC)

    @respx.mock
    async def test_fetch_latest_http_error(self) -> None:
        respx.get("https://notfound.com/feed").mock(return_value=httpx.Response(500))

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)

            with pytest.raises(httpx.HTTPStatusError):
                await adapter.fetch_latest("https://notfound.com/feed")

    @respx.mock
    async def test_fetch_invalid_feed(self) -> None:
        respx.get("https://invalid.com/feed").mock(
            return_value=httpx.Response(200, text="<not valid xml>")
        )

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)
            items = await adapter.fetch_latest("https://invalid.com/feed")

        assert len(items) == 0

    @respx.mock
    async def test_uses_feed_url_parameter(self) -> None:
        respx.get("https://override.com/feed").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)
            items = await adapter.fetch_latest(
                "ignored-identifier", feed_url="https://override.com/feed"
            )

        assert len(items) == 1

    async def test_source_type(self) -> None:
        adapter = RSSAdapter()
        assert adapter.source_type == "rss"

    @respx.mock
    async def test_fallback_to_feed_title_for_author(self) -> None:
        feed_without_author = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Feed Title as Author</title>
            <item>
              <title>No Author Article</title>
              <link>https://blog.com/no-author</link>
              <guid>no-author</guid>
            </item>
          </channel>
        </rss>
        """
        respx.get("https://blog.com/feed").mock(
            return_value=httpx.Response(200, text=feed_without_author)
        )

        async with httpx.AsyncClient() as client:
            adapter = RSSAdapter(http_client=client)
            items = await adapter.fetch_latest("https://blog.com/feed")

        assert len(items) == 1
        assert items[0].author == "Feed Title as Author"
