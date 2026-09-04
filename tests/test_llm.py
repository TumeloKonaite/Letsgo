from __future__ import annotations

import pytest
from app.chatbot.llm import LLMConfigurationError, OpenAIClient
from app.core.config import Settings
from httpx import Request, Response
from openai import AuthenticationError


class _FailingCompletionsClient:
    def create(self, *args, **kwargs):
        raise AuthenticationError(
            "Incorrect API key provided: latest.",
            response=Response(
                401,
                request=Request("POST", "https://api.openai.com/v1/chat/completions"),
            ),
            body={
                "error": {
                    "message": "Incorrect API key provided: latest.",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )


class _FailingChatClient:
    def __init__(self) -> None:
        self.completions = _FailingCompletionsClient()


class _FailingOpenAIClient:
    def __init__(self) -> None:
        self.chat = _FailingChatClient()


def test_openai_client_maps_authentication_error_to_configuration_error() -> None:
    client = OpenAIClient(
        settings=Settings(openai_api_key="latest"),
        client=_FailingOpenAIClient(),
    )

    with pytest.raises(LLMConfigurationError, match="Chat service is unavailable."):
        client.complete([{"role": "user", "content": "Hello"}])
