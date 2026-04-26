from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter request or response handling fails."""


class OpenRouterClient:
    """Small OpenRouter client for JSON-only risk analysis responses."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        api_keys: list[str] | None = None,
        max_retries_per_key: int = 2,
        base_backoff_seconds: float = 0.8,
        max_tokens: int = 220,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        normalized_keys = [key.strip() for key in (api_keys or []) if key and key.strip()]
        if api_key and api_key.strip() and api_key.strip() not in normalized_keys:
            normalized_keys.insert(0, api_key.strip())
        self._api_keys = normalized_keys
        self._model = model
        self._max_retries_per_key = max(0, max_retries_per_key)
        self._base_backoff_seconds = max(0.1, base_backoff_seconds)
        self._max_tokens = max(64, max_tokens)

    async def create_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenRouter chat completions and return model content text."""
        if not self._api_keys:
            raise OpenRouterError("OpenRouter API key is missing. Set GUARDIAN_OPENROUTER_API_KEY.")

        endpoint = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": self._max_tokens,
            "response_format": {"type": "json_object"},
        }
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=40) as client:
            for index, api_key in enumerate(self._api_keys):
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                for attempt in range(self._max_retries_per_key + 1):
                    try:
                        response = await client.post(endpoint, json=payload, headers=headers)
                        response.raise_for_status()
                        body = response.json()
                        choices = body.get("choices", [])
                        if not choices:
                            raise OpenRouterError("OpenRouter returned no choices.")
                        message = choices[0].get("message", {})
                        content = message.get("content")
                        if not isinstance(content, str) or not content.strip():
                            raise OpenRouterError("OpenRouter returned empty content.")
                        return content
                    except httpx.HTTPStatusError as error:
                        last_error = error
                        if error.response.status_code != 429:
                            raise OpenRouterError(f"OpenRouter request failed: {error}") from error

                        retry_after_seconds = _parse_retry_after_seconds(error.response)
                        if attempt < self._max_retries_per_key:
                            backoff_seconds = (
                                retry_after_seconds
                                if retry_after_seconds is not None
                                else self._base_backoff_seconds * (2**attempt) + random.uniform(0.05, 0.25)
                            )
                            await asyncio.sleep(backoff_seconds)
                            continue
                        if index < len(self._api_keys) - 1:
                            # Move to the next key when this key exhausted retries.
                            await asyncio.sleep(0.2)
                            break
                        raise OpenRouterError(f"OpenRouter request failed: {error}") from error
                    except (httpx.HTTPError, OpenRouterError) as error:
                        last_error = error
                        raise OpenRouterError(f"OpenRouter request failed: {error}") from error

        raise OpenRouterError(f"OpenRouter request failed: {last_error}")


def _parse_retry_after_seconds(response: httpx.Response) -> float | None:
    """Parse Retry-After header seconds, when provided by upstream."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        value = float(retry_after)
    except ValueError:
        return None
    return value if value > 0 else None

