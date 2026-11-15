"""Abstract provider interfaces for search and LLM calls.

All pipeline modules must use these interfaces — never call Tavily or OpenAI directly.
"""

from abc import ABC, abstractmethod

from intelligence.contracts import ResearchContext, SourceRecord


class SearchProviderError(Exception):
    """Raised when a search provider call fails."""


class LLMParseError(Exception):
    """Raised when an LLM response cannot be parsed into the expected JSON structure."""


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, context: ResearchContext) -> list[SourceRecord]:
        """Execute a search query and return normalised source records."""
        ...


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the raw response string."""
        ...
