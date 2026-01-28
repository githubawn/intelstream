from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DiscoveredPost:
    url: str
    title: str
    published_at: datetime | None = None


@dataclass
class DiscoveryResult:
    posts: list[DiscoveredPost]
    feed_url: str | None = None
    url_pattern: str | None = None


class DiscoveryStrategy(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def discover(
        self,
        url: str,
        url_pattern: str | None = None,
    ) -> DiscoveryResult | None:
        """
        Attempt to discover posts from the given URL.

        Args:
            url: The page URL to discover posts from.
            url_pattern: Optional URL pattern to filter posts (used by sitemap strategy).

        Returns:
            DiscoveryResult with posts if strategy works, None if not applicable.
        """
        pass
