"""Centralized LLM usage tracking and telemetry.

Audits actual API requests, retry attempts, token consumption, latency,
cache hits, and failure categories across all pipeline stages.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import threading
from typing import Dict, List, Optional

from intelligence.contracts import LLMUsageReport

logger = logging.getLogger("changeradar.intelligence.instrumentation")


@dataclass
class LLMRequestEvent:
    """Telemetry record for a single LLM request attempt."""

    timestamp: datetime
    run_id: str
    stage: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    is_retry: bool
    is_cache_hit: bool
    success: bool
    error_category: Optional[str] = None


class LLMUsageTracker:
    """Thread-safe usage tracker for a research run lifecycle."""

    def __init__(self, run_id: str = "default_run"):
        self.run_id = run_id
        self._lock = threading.Lock()
        self._events: List[LLMRequestEvent] = []

    def record_request(
        self,
        stage: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: float = 0.0,
        is_retry: bool = False,
        is_cache_hit: bool = False,
        success: bool = True,
        error_category: Optional[str] = None,
    ) -> None:
        """Record an LLM request event."""
        event = LLMRequestEvent(
            timestamp=datetime.now(timezone.utc),
            run_id=self.run_id,
            stage=stage,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            is_retry=is_retry,
            is_cache_hit=is_cache_hit,
            success=success,
            error_category=error_category,
        )
        with self._lock:
            self._events.append(event)

        logger.debug(
            f"LLM telemetry [{stage}] {provider}/{model} - cache_hit={is_cache_hit} retry={is_retry} "
            f"in_tok={input_tokens} out_tok={output_tokens} duration={duration_ms:.1f}ms success={success}"
        )

    def get_summary(self) -> LLMUsageReport:
        """Generate a summarized LLMUsageReport contract."""
        with self._lock:
            events = list(self._events)

        total_requests = 0
        total_in_tokens = 0
        total_out_tokens = 0
        cache_hits = 0
        cache_misses = 0
        retries = 0
        stages_count: Dict[str, int] = {}

        for ev in events:
            if ev.is_cache_hit:
                cache_hits += 1
            else:
                total_requests += 1
                cache_misses += 1
                total_in_tokens += ev.input_tokens
                total_out_tokens += ev.output_tokens
                if ev.is_retry:
                    retries += 1
                stages_count[ev.stage] = stages_count.get(ev.stage, 0) + 1

        return LLMUsageReport(
            total_requests=total_requests,
            total_input_tokens=total_in_tokens,
            total_output_tokens=total_out_tokens,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            retries=retries,
            stages=stages_count,
        )

    def get_events(self) -> List[LLMRequestEvent]:
        """Return raw telemetry event list for inspection or test assertions."""
        with self._lock:
            return list(self._events)

    def reset(self) -> None:
        """Clear recorded events."""
        with self._lock:
            self._events.clear()


# Default thread-local/global tracker instance
_ACTIVE_TRACKER: Optional[LLMUsageTracker] = None
_TRACKER_LOCK = threading.Lock()


def get_current_tracker() -> LLMUsageTracker:
    global _ACTIVE_TRACKER
    with _TRACKER_LOCK:
        if _ACTIVE_TRACKER is None:
            _ACTIVE_TRACKER = LLMUsageTracker()
        return _ACTIVE_TRACKER


def set_current_tracker(tracker: LLMUsageTracker) -> None:
    global _ACTIVE_TRACKER
    with _TRACKER_LOCK:
        _ACTIVE_TRACKER = tracker

