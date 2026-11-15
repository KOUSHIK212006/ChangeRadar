"""Abstract provider interfaces for search and LLM calls.

All pipeline modules must use these interfaces — never call Tavily, Gemini, or Groq directly.
"""

from abc import ABC, abstractmethod
from typing import Optional

from intelligence.contracts import ResearchContext, SourceRecord


class SearchProviderError(Exception):
    """Raised when a search provider call fails."""
    pass


class LLMError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMParseError(LLMError):
    """Raised when an LLM response cannot be parsed into the expected JSON structure."""
    pass


class QuotaExhaustedError(LLMError):
    """Raised when Gemini or LLM API quota (HTTP 429 / RESOURCE_EXHAUSTED) is exhausted."""
    pass


class PermanentLLMError(LLMError):
    """Raised on non-retryable client errors (e.g., 401 Unauthorized, 403 Forbidden, 400 Bad Request)."""
    pass


class TransientLLMError(LLMError):
    """Raised on temporary errors eligible for backoff retry (e.g. 503, 504, connection timeouts)."""
    pass


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, context: ResearchContext) -> list[SourceRecord]:
        """Execute a search query and return normalised source records."""
        ...


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, stage: str = "general") -> str:
        """Send a chat completion request and return the raw response string."""
        ...
