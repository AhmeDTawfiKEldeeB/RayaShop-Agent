from src.config.settings import settings
from src.infrastructure.embeddings.interface import EmbeddingProvider
from src.infrastructure.embeddings.providers.gemini import GeminiEmbeddingProvider
from src.infrastructure.embeddings.providers.huggingface import HuggingFaceEmbeddingProvider


class EmbeddingFactory:
    _providers: dict[str, type[EmbeddingProvider]] = {
        "huggingface": HuggingFaceEmbeddingProvider,
        "gemini": GeminiEmbeddingProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None, **kwargs) -> EmbeddingProvider:
        name = provider_name or settings.embedding.provider
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise ValueError(
                f"Unknown embedding provider: {name}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )
        return provider_class(**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[EmbeddingProvider]) -> None:
        cls._providers[name] = provider_class
