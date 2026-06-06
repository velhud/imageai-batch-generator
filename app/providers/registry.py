from __future__ import annotations

from typing import Dict, List

from app.models import ModelInfo, ProviderInfo
from .base import BaseProvider
from .google_provider import GoogleGeminiProvider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self.providers: Dict[str, BaseProvider] = {}
        self.register(MockProvider())
        self.register(GoogleGeminiProvider())
        self.register(OpenAIProvider())

    def register(self, provider: BaseProvider) -> None:
        self.providers[provider.id] = provider

    def provider_ids(self) -> List[str]:
        return list(self.providers.keys())

    def get(self, provider_id: str) -> BaseProvider:
        return self.providers[provider_id]

    def info_list(self) -> List[ProviderInfo]:
        items: List[ProviderInfo] = []
        for provider in self.providers.values():
            models: List[ModelInfo] = provider.available_models()
            info = ProviderInfo(
                id=provider.id,
                name=provider.name,
                models=models,
                rate_limit_note=getattr(provider, "rate_limit_note", ""),
            )
            items.append(info)
        return items
