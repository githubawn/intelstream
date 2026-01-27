from typing import TYPE_CHECKING

import discord
import structlog

from intelstream.database.models import ContentItem, SourceType

if TYPE_CHECKING:
    from intelstream.bot import IntelStreamBot

logger = structlog.get_logger()

SOURCE_TYPE_LABELS: dict[SourceType, str] = {
    SourceType.SUBSTACK: "Substack",
    SourceType.YOUTUBE: "YouTube",
    SourceType.RSS: "RSS",
    SourceType.PAGE: "Web",
}

MAX_MESSAGE_LENGTH = 2000


class ContentPoster:
    def __init__(self, bot: "IntelStreamBot") -> None:
        self._bot = bot

    def format_message(
        self,
        content_item: ContentItem,
        source_type: SourceType,
        source_name: str,
    ) -> str:
        parts = []

        if content_item.author:
            parts.append(f"**{content_item.author}**")

        title = content_item.title
        if content_item.original_url:
            parts.append(f"[{title}]({content_item.original_url})")
        else:
            parts.append(f"**{title}**")

        parts.append("")

        summary = content_item.summary or "No summary available."
        parts.append(summary)

        source_label = SOURCE_TYPE_LABELS.get(source_type, "Unknown")
        parts.append("")
        parts.append(f"*{source_label} | {source_name}*")

        message = "\n".join(parts)

        if len(message) > MAX_MESSAGE_LENGTH:
            truncate_at = MAX_MESSAGE_LENGTH - 50
            message = message[:truncate_at] + "...\n\n*[Message truncated]*"

        return message

    async def post_content(
        self,
        channel: discord.TextChannel,
        content_item: ContentItem,
        source_type: SourceType,
        source_name: str,
    ) -> discord.Message:
        content = self.format_message(content_item, source_type, source_name)
        message = await channel.send(content=content)

        logger.info(
            "Posted content to Discord",
            content_id=content_item.id,
            channel_id=channel.id,
            message_id=message.id,
        )

        return message

    async def post_unposted_items(self, guild_id: int) -> int:
        config = await self._bot.repository.get_discord_config(str(guild_id))

        if config is None:
            logger.info(
                "No Discord config for guild - run /config channel to set up posting",
                guild_id=guild_id,
            )
            return 0

        if not config.is_active:
            logger.info("Discord config is inactive for guild", guild_id=guild_id)
            return 0

        channel = self._bot.get_channel(int(config.channel_id))
        if channel is None or not isinstance(channel, discord.TextChannel):
            logger.warning(
                "Could not find output channel - check bot permissions and channel ID",
                guild_id=guild_id,
                channel_id=config.channel_id,
            )
            return 0

        items = await self._bot.repository.get_unposted_content_items()

        if not items:
            logger.debug("No unposted content items to post")
            return 0

        posted_count = 0

        for item in items:
            try:
                source = await self._bot.repository.get_source_by_id(item.source_id)
                if source is None:
                    logger.warning("Source not found for content item", item_id=item.id)
                    continue

                message = await self.post_content(
                    channel=channel,
                    content_item=item,
                    source_type=source.type,
                    source_name=source.name,
                )

                await self._bot.repository.mark_content_item_posted(
                    content_id=item.id,
                    discord_message_id=str(message.id),
                )

                posted_count += 1

            except discord.HTTPException as e:
                logger.error(
                    "Failed to post content item",
                    item_id=item.id,
                    error=str(e),
                )
            except Exception as e:
                logger.error(
                    "Unexpected error posting content item",
                    item_id=item.id,
                    error=str(e),
                )

        logger.info("Posted unposted items", count=posted_count, guild_id=guild_id)
        return posted_count
