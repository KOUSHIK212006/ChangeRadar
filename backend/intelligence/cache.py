"""Content-addressable caching layer for LLM requests and pipeline artifacts.

Prevents repeated LLM calls for identical queries, article bodies, and claim assessments.
Uses SHA-256 content hashing of prompts, model IDs, and prompt versions.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import threading
from typing import Any, Dict, Optional, Tuple

from intelligence.config import intelligence_settings

logger = logging.getLogger("changeradar.intelligence.cache")

PROMPT_VERSION = "v2"


class LLMCache:
    """Thread-safe LRU/TTL content cache."""

    def __init__(self, ttl_seconds: Optional[int] = None, max_entries: int = 1000):
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else intelligence_settings.CACHE_TTL_SECONDS
        self._max_entries = max_entries
        self._lock = threading.Lock()
        # hash_key -> (content, timestamp, metadata)
        self._store: Dict[str, Tuple[str, datetime, Dict[str, Any]]] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def compute_key(
        model: str,
        system_prompt: str,
        user_prompt: str,
        version: str = PROMPT_VERSION,
        provider: str = "default",
        temperature: float = 0.0,
        json_mode: bool = True,
    ) -> str:
        """Generate deterministic SHA-256 cache key incorporating provider, model, version, settings, and prompts."""
        payload = f"{provider}:{model}:{version}:{temperature}:{json_mode}:{system_prompt.strip()}:{user_prompt.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Generate SHA-256 fingerprint for arbitrary content strings."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]

    def get(self, key: str) -> Optional[str]:
        """Retrieve cached completion if present and not expired."""
        if not intelligence_settings.ENABLE_LLM_CACHE:
            return None

        with self._lock:
            if key not in self._store:
                self.misses += 1
                return None

            content, timestamp, meta = self._store[key]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age > self._ttl_seconds:
                del self._store[key]
                self.misses += 1
                return None

            self.hits += 1
            logger.debug(f"Cache HIT for key {key[:12]}... (age: {age:.0f}s)")
            return content

    def set(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store completion in cache with timestamp."""
        if not intelligence_settings.ENABLE_LLM_CACHE:
            return

        with self._lock:
            # Evict oldest if reaching capacity
            if len(self._store) >= self._max_entries:
                oldest_key = min(self._store.keys(), key=lambda k: self._store[k][1])
                del self._store[oldest_key]

            self._store[key] = (value, datetime.now(timezone.utc), metadata or {})
            logger.debug(f"Cache SET for key {key[:12]}...")

    def clear(self) -> None:
        """Clear all cached entries and stats."""
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def size(self) -> int:
        """Return number of cached entries."""
        with self._lock:
            return len(self._store)


# Global default cache singleton
_DEFAULT_CACHE = LLMCache()


def get_cache() -> LLMCache:
    return _DEFAULT_CACHE

