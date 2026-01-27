# IntelStream

A Discord bot that monitors content sources and posts AI-generated summaries to a Discord channel.

## Features

- **Substack newsletters** - Monitor any Substack publication via RSS
- **YouTube channels** - Track new videos with transcript-based summarization
- **RSS/Atom feeds** - Support for any standard RSS or Atom feed
- **Arxiv papers** - Monitor research paper categories (cs.AI, cs.LG, cs.CL, etc.)
- **Web pages** - AI-powered extraction from any blog or news site using automatic CSS selector detection
- **Manual summarization** - Summarize any URL on-demand with `/summarize`
- **AI summaries** - Claude-powered summaries with thesis and key arguments format

## Requirements

- Python 3.12+
- Discord Bot Token
- Anthropic API Key (for Claude)
- YouTube API Key (optional, for YouTube monitoring)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/intelstream.git
   cd intelstream
   ```

2. Install dependencies using uv:
   ```bash
   uv sync
   ```

3. Create a `.env` file with your configuration:
   ```bash
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_GUILD_ID=your_guild_id
   DISCORD_CHANNEL_ID=your_channel_id
   DISCORD_OWNER_ID=your_user_id
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

4. Run the bot:
   ```bash
   uv run intelstream
   ```

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token |
| `DISCORD_GUILD_ID` | The Discord server ID |
| `DISCORD_CHANNEL_ID` | The channel ID for posting summaries |
| `DISCORD_OWNER_ID` | Your Discord user ID (for error notifications) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `YOUTUBE_API_KEY` | - | YouTube Data API key (required for YouTube monitoring) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/intelstream.db` | Database connection string |
| `DEFAULT_POLL_INTERVAL_MINUTES` | `5` | Default polling interval for new sources (1-60) |
| `CONTENT_POLL_INTERVAL_MINUTES` | `5` | Interval for checking and posting new content (1-60) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Summarization Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SUMMARY_MAX_TOKENS` | `2048` | Maximum tokens for AI-generated summaries (256-8192) |
| `SUMMARY_MAX_INPUT_LENGTH` | `100000` | Maximum input content length before truncation (1000-500000) |
| `SUMMARY_MODEL` | `claude-3-5-haiku-20241022` | Claude model to use for summarization |
| `DISCORD_MAX_MESSAGE_LENGTH` | `2000` | Maximum Discord message length (500-2000) |

## Usage

### Getting Started

1. **Invite the bot** to your Discord server with permissions: Send Messages, Use Slash Commands

2. **Set the output channel** where content summaries will be posted:
   ```
   /config channel #your-channel-name
   ```

3. **Add content sources** to monitor:
   ```
   /source add type:Substack name:"My Newsletter" url:https://example.substack.com
   /source add type:YouTube name:"Tech Channel" url:https://youtube.com/@channel
   /source add type:RSS name:"Blog Feed" url:https://example.com/feed.xml
   /source add type:Arxiv name:"ML Papers" url:cs.LG
   /source add type:Page name:"Company Blog" url:https://example.com/blog
   ```

4. The bot will automatically poll sources, fetch new content, generate AI summaries, and post them to your configured channel.

### Discord Commands

#### Source Management

| Command | Description |
|---------|-------------|
| `/source add type:<type> name:<name> url:<url>` | Add a new content source |
| `/source list` | List all configured sources with their status |
| `/source remove name:<name>` | Remove a source by name |
| `/source toggle name:<name>` | Enable or disable a source |

**Supported source types:**
- `Substack` - Substack newsletter URL
- `YouTube` - YouTube channel URL (requires YouTube API key)
- `RSS` - Any RSS/Atom feed URL
- `Arxiv` - Arxiv category code (e.g., `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `stat.ML`)
- `Page` - Any web page URL (uses AI to detect content structure)

#### Configuration

| Command | Description |
|---------|-------------|
| `/config channel #channel` | Set the channel where summaries will be posted |
| `/config show` | Show current bot configuration |

#### Manual Summarization

| Command | Description |
|---------|-------------|
| `/summarize url:<url>` | Get an AI summary of any URL (YouTube, Substack, or web page) |

### How It Works

1. **Polling**: The bot periodically checks all active sources for new content
2. **Fetching**: New articles/videos are fetched and stored in the database
3. **Summarization**: Claude AI generates structured summaries with thesis and key arguments
4. **Posting**: Plain text messages are posted with the summary, author, title link, and source

### Source-Specific Behavior

**YouTube**: Fetches video transcripts (manual or auto-generated) for summarization. Falls back to video description if no transcript is available.

**Arxiv**: Monitors RSS feeds for specific categories. Summaries focus on the problem solved, key innovation, and practical implications.

**Page**: When you add a Page source, the bot uses Claude to analyze the page structure and automatically determine CSS selectors for extracting posts. This allows monitoring blogs and news sites that don't have RSS feeds.

## Development

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

```bash
uv run mypy src/
```

### Project Structure

```
src/intelstream/
├── adapters/          # Source adapters (Substack, YouTube, RSS, Arxiv, Page)
├── database/          # SQLAlchemy models and repository
├── discord/cogs/      # Discord command handlers
├── services/          # Business logic (pipeline, summarizer, content poster)
├── bot.py             # Discord bot main class
├── config.py          # Pydantic settings
└── main.py            # Entry point
```

## License

MIT
