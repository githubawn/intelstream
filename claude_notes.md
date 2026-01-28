# IntelStream Development Notes

This document summarizes the development work completed on IntelStream, a Discord bot for content aggregation and AI-powered summarization.

## Project Overview

IntelStream monitors content sources (Substack newsletters, YouTube channels, RSS feeds) and automatically posts AI-generated summaries to a Discord channel. The bot uses Claude for summarization and discord.py for Discord integration.

## Architecture

```
intelstream/
├── src/intelstream/
│   ├── bot.py                 # Discord bot main class
│   ├── config.py              # Pydantic settings
│   ├── adapters/              # Source adapters
│   │   ├── base.py            # Adapter protocol
│   │   ├── substack.py        # Substack RSS adapter
│   │   ├── youtube.py         # YouTube Data API adapter
│   │   ├── rss.py             # Generic RSS adapter
│   │   └── page.py            # Web page adapter with CSS selectors
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── repository.py      # Database operations
│   ├── discord/cogs/
│   │   ├── source_management.py   # /source commands
│   │   ├── config_management.py   # /config commands
│   │   └── content_posting.py     # Background posting task
│   └── services/
│       ├── pipeline.py        # Content pipeline orchestrator
│       ├── summarizer.py      # Claude summarization
│       └── content_poster.py  # Discord embed creation
└── tests/                     # Unit tests (227 total)
```

## Development Phases

### Phase 1: Infrastructure

**Objective**: Set up project foundation with database, bot framework, and configuration.

**Files Created**:
- `src/intelstream/database/models.py` - SQLAlchemy async models
  - `Source`: Content sources with type, identifier, feed URL, polling state
  - `ContentItem`: Fetched content with title, summary, URL, timestamps
  - `DiscordConfig`: Per-guild configuration for output channel
  - `SourceType` enum: SUBSTACK, YOUTUBE, RSS

- `src/intelstream/database/repository.py` - Repository pattern
  - CRUD operations for sources and content items
  - Deduplication via `get_or_create_content_item()`
  - Batch operations for efficient database access

- `src/intelstream/config.py` - Pydantic Settings
  - Environment variable loading with validation
  - Discord tokens, API keys, database URL
  - Configurable poll intervals and log levels

- `src/intelstream/bot.py` - IntelStreamBot class
  - Async SQLAlchemy session management
  - Repository injection
  - Owner notification system
  - Cog loading in setup_hook()

**Key Decisions**:
- Used SQLAlchemy 2.0 async for database operations
- Used Pydantic v2 for settings with `model_config`
- Structured logging with structlog

### Phase 2: Source Adapters

**Objective**: Create adapters for fetching content from different source types.

**Files Created**:
- `src/intelstream/adapters/base.py` - Protocol definition
  - `SourceAdapter` protocol with `fetch_new_items()` method
  - `FetchedItem` dataclass for adapter output

- `src/intelstream/adapters/substack.py` - Substack adapter
  - Parses Substack RSS feeds using feedparser
  - Extracts title, content, author, published date
  - Handles both substack.com and custom domain URLs

- `src/intelstream/adapters/youtube.py` - YouTube adapter
  - Uses YouTube Data API v3
  - Resolves channel handles (@username) to channel IDs
  - Fetches video metadata and thumbnails
  - Constructs RSS feed URL for channel

- `src/intelstream/adapters/rss.py` - Generic RSS adapter
  - Supports RSS 2.0 and Atom feeds
  - Extracts standard feed fields
  - Handles various date formats

- `src/intelstream/adapters/factory.py` - Adapter factory
  - Creates appropriate adapter based on SourceType
  - Injects YouTube API key when needed

**Key Decisions**:
- Used feedparser for RSS/Atom parsing (handles edge cases well)
- YouTube requires API key; Substack/RSS work without authentication
- Adapters are stateless and receive configuration at creation

### Phase 3: Content Pipeline

**Objective**: Create orchestration layer for fetching and summarizing content.

**Files Created**:
- `src/intelstream/services/summarizer.py` - SummarizationService
  - Uses Anthropic Python SDK with async client
  - Configurable model (default: claude-sonnet-4-20250514)
  - Generates concise 2-3 sentence summaries
  - Includes source context in prompts

- `src/intelstream/services/pipeline.py` - ContentPipeline
  - Orchestrates fetch and summarization cycles
  - `run_cycle()`: Fetches all sources, then summarizes pending items
  - `_fetch_source()`: Handles individual source with error isolation
  - `_summarize_pending()`: Batch processes unsummarized content
  - Manages aiohttp session lifecycle

**Key Decisions**:
- Pipeline runs as single cycle, called by Discord background task
- Each source fetch is isolated (one failure doesn't stop others)
- Summarization happens after all fetching completes
- Used aiohttp ClientSession for HTTP requests in adapters

### Phase 4: Discord Integration

**Objective**: Connect pipeline to Discord with slash commands and automated posting.

**Files Created**:
- `src/intelstream/services/content_poster.py` - ContentPoster
  - Creates rich Discord embeds from ContentItem
  - Source-specific colors (orange/red/blue for Substack/YouTube/RSS)
  - Source-specific icons in footer
  - Truncates long titles/descriptions to Discord limits
  - `post_unposted_items()`: Posts all pending items for a guild

- `src/intelstream/discord/cogs/source_management.py` - SourceManagement cog
  - `/source add type:<type> name:<name> url:<url>` - Add source
  - `/source list` - List all sources with status
  - `/source remove name:<name>` - Remove source
  - `/source toggle name:<name>` - Enable/disable source
  - `parse_source_identifier()`: Extracts identifiers from URLs

- `src/intelstream/discord/cogs/config_management.py` - ConfigManagement cog
  - `/config channel #channel` - Set output channel
  - `/config show` - Display current configuration
  - Permission checks for bot access to channel

- `src/intelstream/discord/cogs/content_posting.py` - ContentPosting cog
  - Background task with `@tasks.loop()`
  - Runs pipeline cycle on interval
  - Posts to all configured guilds
  - Error handling with owner notification

**Key Decisions**:
- Used discord.py app_commands for slash commands
- Commands grouped under `/source` and `/config`
- Background task interval configurable via settings
- Embeds use images for YouTube thumbnails

## Testing

**Total Tests**: 137 passing

**Test Files**:
- `tests/test_database/test_models.py` - Model validation
- `tests/test_database/test_repository.py` - Repository operations
- `tests/test_adapters/test_substack.py` - Substack adapter
- `tests/test_adapters/test_youtube.py` - YouTube adapter
- `tests/test_adapters/test_rss.py` - RSS adapter
- `tests/test_services/test_summarizer.py` - Summarization service
- `tests/test_services/test_pipeline.py` - Pipeline orchestration
- `tests/test_services/test_content_poster.py` - Content poster
- `tests/test_discord/test_source_management.py` - Source commands
- `tests/test_discord/test_config_management.py` - Config commands
- `tests/test_discord/test_content_posting.py` - Background task

**Testing Patterns**:
- Used pytest with pytest-asyncio for async tests
- Extensive use of `unittest.mock.AsyncMock` for async mocking
- Discord command tests call `.callback()` method directly
- Database tests use in-memory SQLite

## Technical Challenges Resolved

### Discord.py Command Testing
Discord app_commands decorated methods can't be called directly in tests. Solution: call the `.callback()` method with the cog instance as first argument.

```python
# Instead of:
await cog.command(interaction, arg=value)

# Use:
await cog.command.callback(cog, interaction, arg=value)
```

### Mypy Type Errors
1. **Union type attribute access**: `channel.mention` on union of channel types. Fixed with `hasattr()` check.
2. **Loop.error decorator**: discord.py typing issue. Fixed with `# type: ignore[type-var]`.

### Discord Embed.Empty Deprecation
Newer discord.py versions removed `discord.Embed.Empty`. Changed tests to check for `None` instead.

## Configuration

**Required Environment Variables**:
- `DISCORD_BOT_TOKEN` - Bot authentication
- `DISCORD_GUILD_ID` - Server ID for command sync
- `DISCORD_OWNER_ID` - User ID for error notifications
- `ANTHROPIC_API_KEY` - Claude API access

**Optional Environment Variables**:
- `YOUTUBE_API_KEY` - Required only for YouTube sources
- `DATABASE_URL` - Defaults to SQLite
- `CONTENT_POLL_INTERVAL_MINUTES` - Defaults to 5
- `DEFAULT_POLL_INTERVAL_MINUTES` - Source poll interval
- `LOG_LEVEL` - Logging verbosity

## Dependencies

**Runtime**:
- discord.py ~= 2.5 - Discord API wrapper
- SQLAlchemy[asyncio] ~= 2.0 - Async ORM
- aiosqlite - SQLite async driver
- pydantic-settings - Configuration management
- anthropic - Claude API client
- aiohttp - Async HTTP client
- feedparser - RSS/Atom parsing
- structlog - Structured logging

**Development**:
- pytest, pytest-asyncio - Testing
- ruff - Linting and formatting
- mypy - Type checking

## Pull Requests

1. **Phase 1**: Infrastructure setup (merged)
2. **Phase 2**: Source adapters (merged)
3. **Phase 3**: Content pipeline (merged)
4. **Phase 4**: Discord integration (PR #3, merged)
5. **Smart Page Adapter**: Add support for non-RSS blog sites with Claude-powered extraction (PR #6, merged)
6. **Restrict Commands**: Restrict commands to admin channel and require permissions (PR #14, merged)
7. **Limit Initial Fetch**: Only fetch 1 article on first poll of new source (PR #15, pending review)
8. **Plain Text Posts**: Replace embed-based posting with plain text formatting (PR #16, pending review)

All PRs included greptile code review via @greptile comment.

## Recent Work (January 2026)

### PR #15: Limit Initial Source Fetch
When adding a new source, the bot was summarizing ~10 articles from the new source. Changed behavior to only fetch the most recent article on first poll (as confirmation), then fetch all new articles on subsequent polls.

**Changes**:
- Modified `_fetch_source()` in `pipeline.py` to detect first poll via `source.last_polled_at is None`
- On first poll, break after storing the first content item
- Added tests for both first-poll and subsequent-poll behaviors

### PR #16: Plain Text Formatting
Discord embeds appear in a colored box. Changed to plain text messages that look like regular user messages while maintaining formatting.

**Changes**:
- Replaced `create_embed()` method with `format_message()` in `content_poster.py`
- Messages use Discord markdown: `**bold**` for author, `[title](url)` for links, `*italics*` for source footer
- Changed `post_content()` to use `channel.send(content=...)` instead of embeds
- Updated all tests to verify plain text formatting behavior

### Smart Page Adapter (Merged)
Added support for blogs without RSS feeds using Claude-powered page analysis.

**New Files**:
- `src/intelstream/adapters/page.py` - Extracts content using CSS selectors from Claude-generated profile
- `src/intelstream/services/page_analyzer.py` - Uses Claude to analyze page structure and generate extraction profiles
- New `SourceType.PAGE` added to models

**How it works**:
1. User adds a Page source with `/source add type:page name:X url:Y`
2. `PageAnalyzer` fetches the page and asks Claude to identify CSS selectors for posts, titles, links, dates, authors
3. Profile is stored as JSON in `Source.extraction_profile`
4. `PageAdapter` uses the profile to extract posts on subsequent polls

### Code Review (January 2026)
Comprehensive code review of entire codebase for errors and optimization opportunities.

**Review Summary**:
- All source code passes mypy type checking with no issues
- All source code passes ruff linting with no issues
- Production code is well-structured with clean architecture
- 227 tests in total

**Issues Found & Fixed**:
- **Test isolation bug** in `tests/test_config.py`: Tests were not properly isolated from the user's `.env` file. Pydantic-settings reads from `.env` even when environment variables are set via monkeypatch. Fixed by passing `_env_file=None` to Settings constructor in tests and explicitly deleting `YOUTUBE_API_KEY` env var where needed.

**Files Modified**:
- `tests/test_config.py` - Fixed all 4 test methods to use `_env_file=None` for proper isolation

**Verification**:
- All 227 tests now pass
- mypy: Success, no issues found in 26 source files
- ruff: All checks passed

### Feature Roadmap Creation (January 2026)

Created comprehensive implementation plans for upcoming features in `design/FEATURE_ROADMAP.md`:

**Features Planned**:
1. **Smart Blog Adapter** (Section 0 - Priority) - Cascading discovery strategies for non-standard blog sites
2. **Arxiv Adapter** - Monitor academic paper feeds by category
3. **GitHub Releases Adapter** - Monitor repository releases for tool/model updates
4. **Daily Digest Command** - `/digest` command for catch-up summaries
5. **Wallet Tracking** (Future) - Placeholder for cryptocurrency wallet monitoring

### Design Review (January 2026)

Conducted critical review of all feature designs to identify potential issues and gaps.

**Issues Identified & Mitigations Added**:

| Feature | Key Issues | Mitigations |
|---------|------------|-------------|
| Smart Blog Adapter | RSS false positives, fragile pattern inference, content hash sensitivity, no strategy fallback | Content-type validation, LLM-assisted pattern inference, main-content-only hashing, failure counter with auto re-analysis |
| Arxiv Adapter | Volume flooding (100+ papers/day), missed papers during downtime, LaTeX in abstracts | Keyword filtering (MVP requirement), API-based gap recovery, LaTeX stripping/conversion |
| GitHub Adapter | Rate limiting math fails at scale, enormous release notes, pre-release ambiguity | Atom feed as primary (no API limits), smart truncation, configurable pre-release handling |
| Daily Digest | No spam protection, query performance, category imbalance | Cooldown decorator (MVP requirement), database indexes, balanced per-category limits |

**Cross-Cutting Concerns Documented**:
1. Error recovery and retry logic (shared utility pattern)
2. Circuit breaker pattern for external services
3. Monitoring and metrics collection
4. Configuration management (centralize magic numbers)
5. Multi-guild considerations (defer, document assumptions)
6. Content update handling (ignore for MVP, document)
7. Logging standards

**MVP Requirements Established**:
- Smart Blog Adapter: RSS validation, JSON extraction robustness, strategy fallback
- Arxiv Adapter: Keyword filtering to prevent channel flooding
- GitHub Adapter: Rate limit handling
- Daily Digest: Cooldown to prevent spam

**Files Modified**:
- `design/FEATURE_ROADMAP.md` - Added "Known Issues & Mitigations" sections to all features, added "Cross-Cutting Concerns" section, updated implementation notes with MVP requirements

### Message Forwarding Feature (January 2026)

Implemented the message forwarding feature as designed in `design/MESSAGE_FORWARDING.md`.

**Use Case**: Discord's native "Follow" feature only forwards announcement channel messages to channels, not threads. This feature allows forwarding those messages to a thread for better organization.

**Files Created**:
- `src/intelstream/database/models.py` - Added `ForwardingRule` model
- `src/intelstream/database/repository.py` - Added 6 forwarding rule methods
- `src/intelstream/services/message_forwarder.py` - Message forwarding service
- `src/intelstream/discord/cogs/message_forwarding.py` - Discord cog with slash commands
- `tests/test_database.py` - Added `TestForwardingRuleOperations` class (7 tests)
- `tests/test_services/test_message_forwarder.py` - Forwarder service tests (15 tests)
- `tests/test_discord/test_message_forwarding.py` - Cog tests (18 tests)

**Key Implementation Details**:
- Commands: `/forward add`, `/forward list`, `/forward remove`, `/forward pause`, `/forward resume`
- In-memory cache for efficient `on_message` lookups
- Rate limiting via semaphore (5 concurrent forwards)
- Automatic thread unarchiving for archived destination threads
- Attachment size checking against guild limits
- Bot ignores its own messages to prevent loops

**Status**: PR #27 created (https://github.com/user1303836/intelstream/pull/27)

### Channel-Scoped Sources (January 2026)

Implemented channel-scoped source posting. When a source is added via `/source add` in a specific channel, content for that source will only be posted to that channel.

**Problem**: Previously, all sources were global and content was posted to a single guild-wide channel configured via `/config channel`. Users wanted sources to post to the channel where they were added.

**Solution**: Added `guild_id` and `channel_id` fields to the `Source` model and updated the posting logic to respect per-source channels.

**Files Modified**:
- `src/intelstream/database/models.py` - Added `guild_id` and `channel_id` fields to `Source` model
- `src/intelstream/database/repository.py` - Added migration for new columns, updated `add_source()` signature
- `src/intelstream/discord/cogs/source_management.py` - Capture `channel_id` and `guild_id` from interaction when adding sources, show channel info in `/source list`
- `src/intelstream/services/content_poster.py` - Updated `post_unposted_items()` to post to each source's channel
- `tests/test_database.py` - Added test for source with channel
- `tests/test_services/test_content_poster.py` - Rewrote posting tests for new logic
- `tests/test_discord/test_source_management.py` - Updated tests with guild/channel IDs

**Key Implementation Details**:
- `guild_id` and `channel_id` are nullable for backward compatibility
- Posting logic: first check source's `channel_id`, fall back to guild's `DiscordConfig` if not set
- Items from sources belonging to different guilds are skipped during posting
- Source list now shows which channel each source posts to
