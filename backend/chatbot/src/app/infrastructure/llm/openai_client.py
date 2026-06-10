from __future__ import annotations

from collections.abc import Iterator

from openai import APITimeoutError, OpenAI

from src.app.core.config import Settings


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM integration is requested without valid configuration."""


class OpenAIClient:
    def __init__(
        self,
        settings: Settings,
        client: OpenAI | None = None,
    ) -> None:
        if not settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
        self._model = settings.openai_model
        self._client = client or OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
        except APITimeoutError as exc:
            raise TimeoutError("OpenAI request timed out") from exc
        content = response.choices[0].message.content
        return content or ""

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]:
        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except APITimeoutError as exc:
            raise TimeoutError("OpenAI request timed out") from exc


class UnavailableLLMClient:
    def __init__(self, message: str = "OPENAI_API_KEY is not configured.") -> None:
        self._message = message

    def complete(self, messages: list[dict[str, str]]) -> str:
        raise LLMConfigurationError(self._message)

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]:
        raise LLMConfigurationError(self._message)
