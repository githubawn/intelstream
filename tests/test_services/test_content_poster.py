from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from intelstream.database.models import ContentItem, SourceType
from intelstream.services.content_poster import (
    MAX_EMBED_DESCRIPTION,
    MAX_EMBED_TITLE,
    SOURCE_TYPE_COLORS,
    SOURCE_TYPE_ICONS,
    ContentPoster,
)


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.repository = MagicMock()
    return bot


@pytest.fixture
def content_poster(mock_bot):
    return ContentPoster(mock_bot)


@pytest.fixture
def sample_content_item():
    item = MagicMock(spec=ContentItem)
    item.id = "test-item-id"
    item.title = "Test Article Title"
    item.summary = "This is a test summary of the article."
    item.original_url = "https://example.com/article"
    item.author = "Test Author"
    item.thumbnail_url = "https://example.com/image.jpg"
    item.published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    item.source_id = "test-source-id"
    return item


class TestContentPosterCreateEmbed:
    def test_create_embed_basic(self, content_poster, sample_content_item):
        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="Test Substack",
        )

        assert isinstance(embed, discord.Embed)
        assert embed.title == sample_content_item.title
        assert embed.url == sample_content_item.original_url
        assert embed.description == sample_content_item.summary
        assert embed.color == SOURCE_TYPE_COLORS[SourceType.SUBSTACK]

    def test_create_embed_truncates_long_title(self, content_poster, sample_content_item):
        sample_content_item.title = "A" * (MAX_EMBED_TITLE + 100)

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.RSS,
            source_name="Test RSS",
        )

        assert len(embed.title) == MAX_EMBED_TITLE
        assert embed.title.endswith("...")

    def test_create_embed_truncates_long_description(self, content_poster, sample_content_item):
        sample_content_item.summary = "A" * (MAX_EMBED_DESCRIPTION + 100)

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.RSS,
            source_name="Test RSS",
        )

        assert len(embed.description) == MAX_EMBED_DESCRIPTION
        assert embed.description.endswith("...")

    def test_create_embed_without_summary(self, content_poster, sample_content_item):
        sample_content_item.summary = None

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="Test Substack",
        )

        assert embed.description == "No summary available."

    def test_create_embed_sets_author(self, content_poster, sample_content_item):
        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="Test Substack",
        )

        assert embed.author.name == sample_content_item.author

    def test_create_embed_without_author(self, content_poster, sample_content_item):
        sample_content_item.author = None

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="Test Substack",
        )

        assert embed.author.name is None

    def test_create_embed_sets_thumbnail(self, content_poster, sample_content_item):
        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.YOUTUBE,
            source_name="Test YouTube",
        )

        assert embed.image.url == sample_content_item.thumbnail_url

    def test_create_embed_without_thumbnail(self, content_poster, sample_content_item):
        sample_content_item.thumbnail_url = None

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.YOUTUBE,
            source_name="Test YouTube",
        )

        assert embed.image.url is None

    def test_create_embed_sets_footer(self, content_poster, sample_content_item):
        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="My Newsletter",
        )

        expected_footer = f"{SOURCE_TYPE_ICONS[SourceType.SUBSTACK]} | My Newsletter"
        assert embed.footer.text == expected_footer

    def test_create_embed_colors_by_source_type(self, content_poster, sample_content_item):
        for source_type, expected_color in SOURCE_TYPE_COLORS.items():
            embed = content_poster.create_embed(
                content_item=sample_content_item,
                source_type=source_type,
                source_name="Test",
            )
            assert embed.color == expected_color

    def test_create_embed_uses_published_at_timestamp(self, content_poster, sample_content_item):
        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.RSS,
            source_name="Test RSS",
        )

        assert embed.timestamp == sample_content_item.published_at

    def test_create_embed_uses_current_time_if_no_published_at(
        self, content_poster, sample_content_item
    ):
        sample_content_item.published_at = None

        embed = content_poster.create_embed(
            content_item=sample_content_item,
            source_type=SourceType.RSS,
            source_name="Test RSS",
        )

        assert embed.timestamp is not None


class TestContentPosterPostContent:
    async def test_post_content_sends_embed(self, content_poster, sample_content_item):
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_message = MagicMock(spec=discord.Message)
        mock_message.id = 12345
        mock_channel.send = AsyncMock(return_value=mock_message)

        result = await content_poster.post_content(
            channel=mock_channel,
            content_item=sample_content_item,
            source_type=SourceType.SUBSTACK,
            source_name="Test",
        )

        mock_channel.send.assert_called_once()
        call_kwargs = mock_channel.send.call_args.kwargs
        assert "embed" in call_kwargs
        assert isinstance(call_kwargs["embed"], discord.Embed)
        assert result == mock_message


class TestContentPosterPostUnpostedItems:
    async def test_returns_zero_when_no_config(self, content_poster, mock_bot):
        mock_bot.repository.get_discord_config = AsyncMock(return_value=None)

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0

    async def test_returns_zero_when_config_inactive(self, content_poster, mock_bot):
        mock_config = MagicMock()
        mock_config.is_active = False
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0

    async def test_returns_zero_when_channel_not_found(self, content_poster, mock_bot):
        mock_config = MagicMock()
        mock_config.is_active = True
        mock_config.channel_id = "999"
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)
        mock_bot.get_channel = MagicMock(return_value=None)

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0

    async def test_returns_zero_when_no_items(self, content_poster, mock_bot):
        mock_config = MagicMock()
        mock_config.is_active = True
        mock_config.channel_id = "456"
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel = MagicMock(return_value=mock_channel)

        mock_bot.repository.get_unposted_content_items = AsyncMock(return_value=[])

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0

    async def test_posts_items_and_marks_posted(
        self, content_poster, mock_bot, sample_content_item
    ):
        mock_config = MagicMock()
        mock_config.is_active = True
        mock_config.channel_id = "456"
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_message = MagicMock(spec=discord.Message)
        mock_message.id = 789
        mock_channel.send = AsyncMock(return_value=mock_message)
        mock_bot.get_channel = MagicMock(return_value=mock_channel)

        mock_bot.repository.get_unposted_content_items = AsyncMock(
            return_value=[sample_content_item]
        )

        mock_source = MagicMock()
        mock_source.type = SourceType.SUBSTACK
        mock_source.name = "Test Source"
        mock_bot.repository.get_source_by_id = AsyncMock(return_value=mock_source)
        mock_bot.repository.mark_content_item_posted = AsyncMock()

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 1
        mock_bot.repository.mark_content_item_posted.assert_called_once_with(
            content_id=sample_content_item.id,
            discord_message_id="789",
        )

    async def test_continues_on_http_exception(self, content_poster, mock_bot, sample_content_item):
        mock_config = MagicMock()
        mock_config.is_active = True
        mock_config.channel_id = "456"
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_response = MagicMock()
        mock_response.status = 500
        mock_channel.send = AsyncMock(
            side_effect=discord.HTTPException(mock_response, "Server Error")
        )
        mock_bot.get_channel = MagicMock(return_value=mock_channel)

        mock_bot.repository.get_unposted_content_items = AsyncMock(
            return_value=[sample_content_item]
        )

        mock_source = MagicMock()
        mock_source.type = SourceType.SUBSTACK
        mock_source.name = "Test Source"
        mock_bot.repository.get_source_by_id = AsyncMock(return_value=mock_source)

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0

    async def test_skips_item_when_source_not_found(
        self, content_poster, mock_bot, sample_content_item
    ):
        mock_config = MagicMock()
        mock_config.is_active = True
        mock_config.channel_id = "456"
        mock_bot.repository.get_discord_config = AsyncMock(return_value=mock_config)

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_bot.get_channel = MagicMock(return_value=mock_channel)

        mock_bot.repository.get_unposted_content_items = AsyncMock(
            return_value=[sample_content_item]
        )
        mock_bot.repository.get_source_by_id = AsyncMock(return_value=None)

        result = await content_poster.post_unposted_items(guild_id=123)

        assert result == 0
