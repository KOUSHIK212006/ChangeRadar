"""Tavily search provider adapter.

Calls the Tavily Search API and returns a list of normalised SourceRecords.
Syndication detection happens later in the normalizer pipeline stage.
"""

import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

import httpx

from intelligence.config import intelligence_settings
from intelligence.contracts import ResearchContext, SourceRecord
from intelligence.providers.base import SearchProvider, SearchProviderError

logger = logging.getLogger("changeradar.intelligence.providers.tavily")

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _strip_utm(url: str) -> str:
    """Remove UTM tracking params and trailing slashes from a URL."""
    parsed = urlparse(url)
    utm_keys = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
    filtered = {k: v for k, v in parse_qs(parsed.query).items() if k not in utm_keys}
    clean_query = urlencode(filtered, doseq=True)
    canonical = urlunparse(parsed._replace(query=clean_query))
    return canonical.rstrip("/")


def _source_id(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()[:16]


def _parse_publisher(url: str) -> str:
    host = urlparse(url).netloc
    return host.removeprefix("www.")


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: str | None = None, max_results: int | None = None, timeout: int | None = None):
        self._api_key = api_key or intelligence_settings.TAVILY_API_KEY
        self._max_results = max_results or intelligence_settings.SEARCH_MAX_RESULTS
        self._timeout = timeout or intelligence_settings.SEARCH_TIMEOUT_SECONDS

    def search(self, query: str, context: ResearchContext) -> list[SourceRecord]:
        if not self._api_key:
            raise SearchProviderError("TAVILY_API_KEY is not configured.")

        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": self._max_results,
        }

        try:
            response = httpx.post(TAVILY_SEARCH_URL, json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise SearchProviderError(f"Tavily request timed out: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise SearchProviderError(f"Tavily returned HTTP {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise SearchProviderError(f"Unexpected error calling Tavily: {exc}") from exc

        discovered_at = datetime.now(timezone.utc)
        records: list[SourceRecord] = []

        for item in data.get("results", []):
            url = item.get("url", "")
            canonical_url = _strip_utm(url)
            published_at: datetime | None = None

            raw_date = item.get("published_date")
            if raw_date:
                try:
                    published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Could not parse published_date '{raw_date}' for {url}")

            records.append(
                SourceRecord(
                    source_id=_source_id(canonical_url),
                    url=url,
                    canonical_url=canonical_url,
                    title=item.get("title", ""),
                    publisher=_parse_publisher(url),
                    snippet=item.get("content", ""),
                    published_at=published_at,
                    discovered_at=discovered_at,
                    is_syndicated=False,
                    syndication_confidence=0.0,
                )
            )

        return records
