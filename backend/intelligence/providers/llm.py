"""Groq LLM provider adapter.

Groq exposes an OpenAI-compatible chat completions API.
Always requests JSON output. JSON parsing happens in the calling pipeline module.
"""

import json
import logging
import time

import httpx

from intelligence.config import intelligence_settings
from intelligence.providers.base import LLMParseError, LLMProvider

logger = logging.getLogger("changeradar.intelligence.providers.llm")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        self._api_key = api_key or intelligence_settings.GROQ_API_KEY
        self._model = model or intelligence_settings.LLM_MODEL
        self._temperature = temperature if temperature is not None else intelligence_settings.LLM_TEMPERATURE
        self._timeout = timeout or intelligence_settings.LLM_TIMEOUT_SECONDS
        self._max_retries = max_retries if max_retries is not None else intelligence_settings.MAX_RETRIES

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request to Groq and return the raw response string.

        Retries on transient errors up to MAX_RETRIES times.
        Raises LLMParseError if the response cannot be decoded as JSON.
        """
        if not self._api_key:
            raise LLMParseError("GROQ_API_KEY is not configured.")

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
        }

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = httpx.post(GROQ_CHAT_URL, json=payload, headers=headers, timeout=self._timeout)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]

                # Validate it is parseable JSON before returning
                json.loads(content)
                return content

            except json.JSONDecodeError as exc:
                raise LLMParseError(f"LLM response is not valid JSON: {exc}") from exc
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"Groq request failed (attempt {attempt + 1}), retrying in {wait}s: {exc}")
                    time.sleep(wait)
            except Exception as exc:
                raise LLMParseError(f"Unexpected error calling Groq: {exc}") from exc

        raise LLMParseError(f"Groq request failed after {self._max_retries + 1} attempts: {last_exc}") from last_exc


# Alias so existing imports of OpenAILLMProvider still work without changes
OpenAILLMProvider = GroqLLMProvider
