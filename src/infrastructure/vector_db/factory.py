from src.infrastructure.vector_db.interface import VectorStore
from src.infrastructure.vector_db.providers.qdrant import QdrantDB


class VectorDBFactory:
    _providers: dict[str, type[VectorStore]] = {
        "qdrant": QdrantDB,
    }

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> VectorStore:
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(
                f"Unknown vector DB provider: {provider_name}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )
        return provider_class(**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[VectorStore]) -> None:
        cls._providers[name] = provider_class
