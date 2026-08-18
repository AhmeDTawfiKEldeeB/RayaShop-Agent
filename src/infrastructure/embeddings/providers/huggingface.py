from sentence_transformers import SentenceTransformer

from src.config.settings import settings
from src.infrastructure.embeddings.interface import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.embedding.huggingface.model_name
        self._model = SentenceTransformer(self._model_name)

    def embed_text(self, text: str) -> list[float]:
        embedding = self._model.encode(text)
        return embedding.tolist()

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(documents)
        return embeddings.tolist()
