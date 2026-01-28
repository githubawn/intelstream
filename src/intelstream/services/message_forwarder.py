from asyncio import Semaphore

import discord
import structlog

logger = structlog.get_logger()


class MessageForwarder:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._semaphore = Semaphore(5)

    async def forward_message(
        self,
        message: discord.Message,
        destination_id: int,
        destination_type: str,
    ) -> discord.Message | None:
        async with self._semaphore:
            try:
                destination = await self._get_destination(destination_id, destination_type)
                if destination is None:
                    logger.warning(
                        "Forwarding destination not found",
                        destination_id=destination_id,
                        destination_type=destination_type,
                    )
                    return None

                if isinstance(destination, discord.Thread) and destination.archived:
                    try:
                        await destination.edit(archived=False)
                    except discord.Forbidden:
                        logger.warning("Cannot unarchive thread", thread_id=destination_id)
                        return None

                content = self._build_forwarded_content(message)
                embeds = message.embeds[:10] if message.embeds else []
                files = await self._download_attachments(message, destination)

                forwarded = await destination.send(
                    content=content,
                    embeds=embeds,
                    files=files,
                )

                logger.info(
                    "Message forwarded",
                    source_channel=message.channel.id,
                    destination=destination_id,
                    message_id=message.id,
                )

                return forwarded

            except discord.Forbidden:
                logger.error(
                    "Missing permissions to forward message",
                    destination_id=destination_id,
                )
                return None
            except discord.HTTPException as e:
                logger.error(
                    "Failed to forward message",
                    error=str(e),
                    destination_id=destination_id,
                )
                return None

    async def _get_destination(
        self, destination_id: int, destination_type: str
    ) -> discord.TextChannel | discord.Thread | None:
        if destination_type == "thread":
            channel = self.bot.get_channel(destination_id)
            if isinstance(channel, discord.Thread):
                return channel
            for guild in self.bot.guilds:
                thread = guild.get_thread(destination_id)
                if thread is not None:
                    return thread
            return None
        channel = self.bot.get_channel(destination_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    async def _download_attachments(
        self, message: discord.Message, destination: discord.TextChannel | discord.Thread
    ) -> list[discord.File]:
        files = []
        for attachment in message.attachments[:10]:
            if attachment.size > destination.guild.filesize_limit:
                logger.warning(
                    "Attachment too large to forward",
                    size=attachment.size,
                    limit=destination.guild.filesize_limit,
                )
                continue
            try:
                file = await attachment.to_file()
                files.append(file)
            except discord.HTTPException:
                logger.warning(
                    "Failed to download attachment",
                    attachment_id=attachment.id,
                )
        return files

    def _build_forwarded_content(self, message: discord.Message) -> str:
        parts = []
        source_name = getattr(message.channel, "name", "Unknown")
        parts.append(f"**Forwarded from #{source_name}**")

        if message.author.bot:
            parts.append(f"*Original author: {message.author.name}*")

        if message.content:
            parts.append("")
            parts.append(message.content)

        return "\n".join(parts)
