import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from src.app.core.config import Settings
from src.app.infrastructure.storage import ConversationStore

from .prompt_builder import TwinPromptBuilder


@dataclass
class ChatResult:
    response: str
    session_id: str


@dataclass
class StreamingChatResult:
    session_id: str
    stream: Iterator[str]


@dataclass(frozen=True)
class TwinResourceLoaders:
    prompt_context: Callable[[], dict[str, Any]]
    fallback_personality: Callable[[], str]


class LLMAdapter(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]: ...


class TwinService:
    def __init__(
        self,
        settings: Settings,
        llm_client: LLMAdapter,
        conversation_store: ConversationStore,
        prompt_builder: TwinPromptBuilder,
        resource_loaders: TwinResourceLoaders,
        personality: str | None = None,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client
        self.conversation_store = conversation_store
        self.prompt_builder = prompt_builder
        self.resource_loaders = resource_loaders
        self._personality = personality

    @property
    def personality(self) -> str:
        if self._personality is None:
            self._personality = self.load_personality()
        return self._personality

    @personality.setter
    def personality(self, value: str) -> None:
        self._personality = value

    def load_personality(self) -> str:
        try:
            return self.prompt_builder.build_system_prompt(
                **self.resource_loaders.prompt_context()
            ).strip()
        except Exception:
            return self.resource_loaders.fallback_personality().strip()

    @staticmethod
    def generate_session_id() -> str:
        return str(uuid.uuid4())

    def build_messages(
        self,
        conversation: list[dict[str, str]],
        user_message: str,
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": self.personality}]
        messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        active_session_id = session_id or self.generate_session_id()
        conversation = self.conversation_store.load(active_session_id)
        messages = self.build_messages(conversation, user_message)

        assistant_response = self.llm_client.complete(messages)
        conversation.append({"role": "user", "content": user_message})
        conversation.append({"role": "assistant", "content": assistant_response})
        self.conversation_store.save(active_session_id, conversation)

        return ChatResult(response=assistant_response, session_id=active_session_id)

    def stream_chat(
        self,
        user_message: str,
        session_id: str | None = None,
    ) -> StreamingChatResult:
        active_session_id = session_id or self.generate_session_id()
        conversation = self.conversation_store.load(active_session_id)
        messages = self.build_messages(conversation, user_message)
        stream = self.llm_client.stream_complete(messages)

        def generate() -> Iterator[str]:
            assistant_parts: list[str] = []
            try:
                for content in stream:
                    assistant_parts.append(content)
                    yield content
            finally:
                assistant_response = "".join(assistant_parts).strip()
                if assistant_response:
                    conversation.append({"role": "user", "content": user_message})
                    conversation.append(
                        {"role": "assistant", "content": assistant_response}
                    )
                    self.conversation_store.save(active_session_id, conversation)

        return StreamingChatResult(session_id=active_session_id, stream=generate())

    def list_sessions(self) -> list[dict[str, Any]]:
        return self.conversation_store.list_sessions()
