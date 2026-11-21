"""Tavily search provider adapter.

Calls the Tavily Search API and returns a list of normalised SourceRecords.
Syndication detection happens later in the normalizer pipeline stage.
"""

import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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


def _parse_published_date(raw_date: Optional[str]) -> Optional[datetime]:
    """Parse publication date supporting ISO 8601 and RFC 2822 / HTTP formats."""
    if not raw_date:
        return None
    # 1. Try ISO 8601
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        pass
    # 2. Try RFC 2822 (e.g. 'Tue, 17 Nov 2026 08:35:46 GMT', 'Fri, 13 Nov 2026 13:00:00 GMT')
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    return None


class TavilySearchProvider(SearchProvider):
    def __init__(
        self,
        api_key: str | None = None,
        max_results: int | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        backoff_base: float | None = None,
        backoff_max: float | None = None,
    ):
        self._api_key = intelligence_settings.TAVILY_API_KEY if api_key is None else api_key
        self._max_results = max_results or intelligence_settings.SEARCH_MAX_RESULTS
        self._timeout = timeout or intelligence_settings.SEARCH_TIMEOUT_SECONDS
        self._max_retries = max_retries if max_retries is not None else intelligence_settings.MAX_RETRIES
        self._backoff_base = backoff_base if backoff_base is not None else intelligence_settings.RETRY_BACKOFF_BASE
        self._backoff_max = backoff_max if backoff_max is not None else intelligence_settings.RETRY_BACKOFF_MAX

    def search(self, query: str, context: ResearchContext) -> list[SourceRecord]:
        if not self._api_key:
            raise SearchProviderError("TAVILY_API_KEY is not configured in environment or .env.")

        payload: dict = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": self._max_results,
        }

        # Temporal filtering: Tavily supports 'days' when 'topic' is 'news'
        if context.time_window_days:
            payload["topic"] = "news"
            payload["days"] = context.time_window_days

        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = httpx.post(TAVILY_SEARCH_URL, json=payload, timeout=self._timeout)
                status_code = response.status_code

                if status_code == 429:
                    retry_after_hdr = response.headers.get("Retry-After")
                    retry_after_val: Optional[float] = None
                    if retry_after_hdr:
                        try:
                            retry_after_val = float(retry_after_hdr)
                        except ValueError:
                            pass

                    if attempt < self._max_retries:
                        backoff = min(
                            self._backoff_max,
                            retry_after_val or (self._backoff_base ** attempt + random.uniform(0.1, 0.5)),
                        )
                        logger.warning(
                            f"Tavily 429 rate limit reached (attempt {attempt + 1}/{self._max_retries + 1}). "
                            f"Retrying in {backoff:.2f}s..."
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        raise SearchProviderError(
                            f"Tavily rate limit (HTTP 429) exceeded after {self._max_retries + 1} attempts."
                        )

                elif status_code in (401, 403):
                    # Permanent auth error - do not retry
                    raise SearchProviderError(
                        f"Tavily authentication failed (HTTP {status_code}): {response.text}"
                    )
                elif status_code == 400:
                    # Permanent client request error - do not retry
                    raise SearchProviderError(
                        f"Tavily bad request (HTTP 400): {response.text}"
                    )
                elif status_code >= 500:
                    # Transient server error - retry with backoff
                    if attempt < self._max_retries:
                        backoff = min(
                            self._backoff_max,
                            self._backoff_base ** attempt + random.uniform(0.1, 0.5),
                        )
                        logger.warning(
                            f"Tavily server error ({status_code}) on attempt {attempt + 1}, retrying in {backoff:.2f}s..."
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        raise SearchProviderError(
                            f"Tavily server error (HTTP {status_code}) after {self._max_retries + 1} attempts: {response.text}"
                        )

                response.raise_for_status()
                data = response.json()

                # If news search returned 0 results, fall back to general search
                if not data.get("results") and payload.get("topic") == "news":
                    logger.info("Tavily news topic returned 0 results; retrying with general topic.")
                    fallback_payload = dict(payload)
                    fallback_payload["topic"] = "general"
                    fallback_payload.pop("days", None)
                    fb_resp = httpx.post(TAVILY_SEARCH_URL, json=fallback_payload, timeout=self._timeout)
                    if fb_resp.status_code == 200:
                        data = fb_resp.json()
                break

            except (SearchProviderError,):
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    backoff = min(
                        self._backoff_max,
                        self._backoff_base ** attempt + random.uniform(0.1, 0.5),
                    )
                    logger.warning(
                        f"Tavily network/timeout error (attempt {attempt + 1}/{self._max_retries + 1}), "
                        f"retrying in {backoff:.2f}s: {exc}"
                    )
                    time.sleep(backoff)
                    continue
                else:
                    raise SearchProviderError(
                        f"Tavily request failed after {self._max_retries + 1} attempts due to network/timeout: {exc}"
                    ) from exc
            except Exception as exc:
                raise SearchProviderError(f"Unexpected error calling Tavily: {exc}") from exc
        else:
            raise SearchProviderError(
                f"Tavily request failed after {self._max_retries + 1} attempts: {last_exc}"
            )

        discovered_at = datetime.now(timezone.utc)
        records: list[SourceRecord] = []

        for item in data.get("results", []):
            url = item.get("url", "")
            canonical_url = _strip_utm(url)
            published_at: datetime | None = None

            raw_date = item.get("published_date")
            published_at = _parse_published_date(raw_date)
            if raw_date and not published_at:
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
