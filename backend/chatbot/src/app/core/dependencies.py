from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import FastAPI, Request

from src.app.core.config import Settings
from src.app.core.config import get_settings as load_settings
from src.app.domain.twin.prompt_builder import TwinPromptBuilder
from src.app.domain.twin.service import LLMAdapter, TwinResourceLoaders, TwinService
from src.app.infrastructure.content import FactsLoader, ResourceLoader
from src.app.infrastructure.llm import OpenAIClient, UnavailableLLMClient
from src.app.infrastructure.storage import ConversationStore, FileConversationStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppDependencies:
    settings: Settings
    llm_client: LLMAdapter
    conversation_store: ConversationStore
    facts_loader: FactsLoader
    content_loader: ResourceLoader
    resource_loaders: TwinResourceLoaders
    prompt_builder: TwinPromptBuilder
    twin_service: TwinService


def build_llm_client(settings: Settings) -> LLMAdapter:
    if not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is not configured; chat completions are unavailable."
        )
        return UnavailableLLMClient()
    return OpenAIClient(settings=settings)


def build_conversation_store(settings: Settings) -> ConversationStore:
    return FileConversationStore(storage_dir=settings.conversation_storage_dir)


def build_facts_loader(settings: Settings) -> FactsLoader:
    return FactsLoader(data_dir=settings.content_data_dir)


def build_content_loader(
    settings: Settings,
    facts_loader: FactsLoader | None = None,
) -> ResourceLoader:
    return ResourceLoader(
        data_dir=settings.content_data_dir,
        facts_loader=facts_loader,
    )


def build_resource_loaders(content_loader: ResourceLoader) -> TwinResourceLoaders:
    return TwinResourceLoaders(
        prompt_context=content_loader.build_prompt_context,
        fallback_personality=content_loader.load_fallback_personality,
    )


def build_prompt_builder() -> TwinPromptBuilder:
    return TwinPromptBuilder()


def build_twin_service(
    settings: Settings,
    llm_client: LLMAdapter,
    conversation_store: ConversationStore,
    resource_loaders: TwinResourceLoaders,
    prompt_builder: TwinPromptBuilder,
) -> TwinService:
    return TwinService(
        settings=settings,
        llm_client=llm_client,
        conversation_store=conversation_store,
        resource_loaders=resource_loaders,
        prompt_builder=prompt_builder,
    )


def build_dependencies(settings: Settings) -> AppDependencies:
    llm_client = build_llm_client(settings)
    conversation_store = build_conversation_store(settings)
    facts_loader = build_facts_loader(settings)
    content_loader = build_content_loader(settings, facts_loader=facts_loader)
    resource_loaders = build_resource_loaders(content_loader)
    prompt_builder = build_prompt_builder()
    twin_service = build_twin_service(
        settings=settings,
        llm_client=llm_client,
        conversation_store=conversation_store,
        resource_loaders=resource_loaders,
        prompt_builder=prompt_builder,
    )

    return AppDependencies(
        settings=settings,
        llm_client=llm_client,
        conversation_store=conversation_store,
        facts_loader=facts_loader,
        content_loader=content_loader,
        resource_loaders=resource_loaders,
        prompt_builder=prompt_builder,
        twin_service=twin_service,
    )


def initialize_dependencies(
    app: FastAPI,
    settings: Settings | None = None,
) -> AppDependencies:
    runtime_settings = settings or load_settings()
    dependencies = build_dependencies(runtime_settings)

    app.state.dependencies = dependencies
    return dependencies


def shutdown_dependencies(app: FastAPI) -> None:
    _ = app


def get_dependencies(request: Request) -> AppDependencies:
    return request.app.state.dependencies


def get_settings(request: Request) -> Settings:
    return get_dependencies(request).settings


def get_llm_client(request: Request) -> LLMAdapter:
    return get_dependencies(request).llm_client


def get_conversation_store(request: Request) -> ConversationStore:
    return get_dependencies(request).conversation_store


def get_resource_loaders(request: Request) -> TwinResourceLoaders:
    return get_dependencies(request).resource_loaders


def get_prompt_builder(request: Request) -> TwinPromptBuilder:
    return get_dependencies(request).prompt_builder


def get_twin_service(request: Request) -> TwinService:
    return get_dependencies(request).twin_service
