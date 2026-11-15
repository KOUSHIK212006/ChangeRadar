"""LLM provider adapters with Gemini, Groq, caching, backoff, and telemetry.

Implements exponential backoff with jitter, quota exhaustion detection (HTTP 429),
content-addressable caching, and fine-grained request telemetry.
"""

from abc import abstractmethod
import json
import logging
import random
import time
from typing import Optional, Tuple

import httpx

from intelligence.cache import get_cache
from intelligence.config import intelligence_settings
from intelligence.instrumentation import get_current_tracker
from intelligence.providers.base import (
    LLMError,
    LLMParseError,
    LLMProvider,
    PermanentLLMError,
    QuotaExhaustedError,
    TransientLLMError,
)

logger = logging.getLogger("changeradar.intelligence.providers.llm")


class BaseLLMProvider(LLMProvider):
    """Base provider handling caching, telemetry, backoff retries, and quota policies."""

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        model: str,
        temperature: float,
        timeout: int,
        max_retries: int,
    ):
        self.provider_name = provider_name
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._timeout = timeout
        self._max_retries = max_retries
        self._cache = get_cache()

    @abstractmethod
    def _call_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """Execute physical HTTP call. Returns (content, in_tokens, out_tokens)."""
        ...

    def complete(self, system_prompt: str, user_prompt: str, stage: str = "general") -> str:
        """Complete prompt with caching, backoff retries, and telemetry auditing."""
        cache_key = self._cache.compute_key(self._model, system_prompt, user_prompt)
        cached_result = self._cache.get(cache_key)

        tracker = get_current_tracker()

        if cached_result is not None:
            # Validate valid JSON before returning cached
            try:
                json.loads(cached_result)
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=0.0,
                    is_retry=False,
                    is_cache_hit=True,
                    success=True,
                )
                return cached_result
            except Exception:
                pass  # Fall through to re-execute if cache was corrupt

        if not self._api_key:
            raise PermanentLLMError(
                f"{self.provider_name.upper()}_API_KEY is not configured in environment or .env."
            )

        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            is_retry = attempt > 0
            start_t = time.perf_counter()

            try:
                content, in_tok, out_tok = self._call_api(system_prompt, user_prompt)
                duration_ms = (time.perf_counter() - start_t) * 1000

                # Validate parseable JSON before accepting
                json.loads(content)

                # Store in cache
                self._cache.set(cache_key, content, {"stage": stage, "model": self._model})

                # Record successful telemetry
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    duration_ms=duration_ms,
                    is_retry=is_retry,
                    is_cache_hit=False,
                    success=True,
                )
                return content

            except json.JSONDecodeError as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    duration_ms=duration_ms,
                    is_retry=is_retry,
                    is_cache_hit=False,
                    success=False,
                    error_category="JSONDecodeError",
                )
                raise LLMParseError(f"LLM response is not valid JSON: {exc}") from exc

            except PermanentLLMError as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    duration_ms=duration_ms,
                    is_retry=is_retry,
                    is_cache_hit=False,
                    success=False,
                    error_category="PermanentClientError",
                )
                # Non-retryable permanent error (e.g. 401, 403, 400)
                raise exc

            except QuotaExhaustedError as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000
                last_exc = exc
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    duration_ms=duration_ms,
                    is_retry=is_retry,
                    is_cache_hit=False,
                    success=False,
                    error_category="QuotaExhausted",
                )
                if attempt < self._max_retries:
                    backoff = min(
                        intelligence_settings.RETRY_BACKOFF_MAX,
                        (intelligence_settings.RETRY_BACKOFF_BASE ** attempt) + random.uniform(0.1, 0.5),
                    )
                    logger.warning(
                        f"Rate limit / 429 quota reached on {self.provider_name} (attempt {attempt + 1}). "
                        f"Retrying in {backoff:.2f}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise QuotaExhaustedError(
                        f"Gemini API quota exceeded (HTTP 429) after {self._max_retries + 1} attempts. "
                        f"Please check quota limits or rate allowance."
                    ) from exc

            except (httpx.TimeoutException, httpx.HTTPStatusError, TransientLLMError, Exception) as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000
                last_exc = exc
                tracker.record_request(
                    stage=stage,
                    provider=self.provider_name,
                    model=self._model,
                    duration_ms=duration_ms,
                    is_retry=is_retry,
                    is_cache_hit=False,
                    success=False,
                    error_category=exc.__class__.__name__,
                )
                if attempt < self._max_retries:
                    backoff = min(
                        intelligence_settings.RETRY_BACKOFF_MAX,
                        (intelligence_settings.RETRY_BACKOFF_BASE ** attempt) + random.uniform(0.1, 0.5),
                    )
                    logger.warning(
                        f"{self.provider_name} request failed (attempt {attempt + 1}), retrying in {backoff:.2f}s: {exc}"
                    )
                    time.sleep(backoff)

        raise LLMParseError(
            f"{self.provider_name} request failed after {self._max_retries + 1} attempts: {last_exc}"
        ) from last_exc


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM provider adapter using Google Generative Language REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(
            provider_name="gemini",
            api_key=api_key or intelligence_settings.GEMINI_API_KEY,
            model=model or intelligence_settings.GEMINI_MODEL,
            temperature=temperature if temperature is not None else intelligence_settings.LLM_TEMPERATURE,
            timeout=timeout or intelligence_settings.LLM_TIMEOUT_SECONDS,
            max_retries=max_retries if max_retries is not None else intelligence_settings.MAX_RETRIES,
        )

    def _call_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": self._temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            status_code = response.status_code

            if status_code == 429:
                raise QuotaExhaustedError(f"Gemini API returned 429 Quota Exhausted: {response.text}")
            elif status_code in (401, 403):
                raise PermanentLLMError(f"Gemini Authentication Failed ({status_code}): {response.text}")
            elif status_code == 400:
                raise PermanentLLMError(f"Gemini Bad Request (400): {response.text}")
            elif status_code >= 500:
                raise TransientLLMError(f"Gemini Server Error ({status_code}): {response.text}")

            response.raise_for_status()
            res_data = response.json()

            # Parse Gemini candidates
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise LLMParseError("Gemini returned empty candidate list.")

            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            # Extract token usage metadata if available
            usage_meta = res_data.get("usageMetadata", {})
            in_tok = usage_meta.get("promptTokenCount", len(user_prompt) // 4)
            out_tok = usage_meta.get("candidatesTokenCount", len(content) // 4)

            return content, in_tok, out_tok

        except (QuotaExhaustedError, PermanentLLMError, TransientLLMError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientLLMError(f"Gemini network error: {exc}") from exc
        except Exception as exc:
            raise TransientLLMError(f"Unexpected error communicating with Gemini: {exc}") from exc


class GroqLLMProvider(BaseLLMProvider):
    """Groq LLM provider adapter using OpenAI-compatible chat completions."""

    GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(
            provider_name="groq",
            api_key=api_key or intelligence_settings.GROQ_API_KEY,
            model=model or intelligence_settings.GROQ_MODEL,
            temperature=temperature if temperature is not None else intelligence_settings.LLM_TEMPERATURE,
            timeout=timeout or intelligence_settings.LLM_TIMEOUT_SECONDS,
            max_retries=max_retries if max_retries is not None else intelligence_settings.MAX_RETRIES,
        )

    def _call_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            response = httpx.post(self.GROQ_CHAT_URL, json=payload, headers=headers, timeout=self._timeout)
            status_code = response.status_code

            if status_code == 429:
                raise QuotaExhaustedError(f"Groq 429 Rate Limit: {response.text}")
            elif status_code in (401, 403):
                raise PermanentLLMError(f"Groq Auth Error ({status_code}): {response.text}")
            elif status_code == 400:
                raise PermanentLLMError(f"Groq Bad Request (400): {response.text}")
            elif status_code >= 500:
                raise TransientLLMError(f"Groq Server Error ({status_code}): {response.text}")

            response.raise_for_status()
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]

            usage = res_json.get("usage", {})
            in_tok = usage.get("prompt_tokens", len(user_prompt) // 4)
            out_tok = usage.get("completion_tokens", len(content) // 4)

            return content, in_tok, out_tok

        except (QuotaExhaustedError, PermanentLLMError, TransientLLMError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientLLMError(f"Groq network error: {exc}") from exc
        except Exception as exc:
            raise TransientLLMError(f"Unexpected error communicating with Groq: {exc}") from exc


# Alias for backward-compatibility
OpenAILLMProvider = GroqLLMProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory creating configured LLM provider instance."""
    provider = (provider_name or intelligence_settings.LLM_PROVIDER).lower()

    if provider == "gemini":
        return GeminiLLMProvider(api_key=api_key, model=model)
    elif provider in ("groq", "openai"):
        return GroqLLMProvider(api_key=api_key, model=model)
    else:
        # Default fallback to Gemini
        return GeminiLLMProvider(api_key=api_key, model=model)
