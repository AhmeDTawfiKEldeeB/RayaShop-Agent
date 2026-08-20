from typing import ClassVar

from langchain_core.language_models import BaseChatModel

from src.config.settings import settings
from src.infrastructure.llm.providers.gemini import GeminiProvider
from src.infrastructure.llm.providers.groq import GroqProvider
from src.infrastructure.llm.providers.openrouter import OpenRouterProvider


class LLMFactory:
    _providers: ClassVar[dict[str, type[BaseChatModel]]] = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "groq": GroqProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None, **kwargs) -> BaseChatModel:
        name = provider_name or settings.llm.provider
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise ValueError(
                f"Unknown LLM provider: {name}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )
        return provider_class(**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[BaseChatModel]) -> None:
        cls._providers[name] = provider_class
