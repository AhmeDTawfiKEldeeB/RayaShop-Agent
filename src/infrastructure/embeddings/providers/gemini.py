from google import genai

from src.config.settings import settings
from src.infrastructure.embeddings.interface import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or settings.embedding.gemini.api_key
        self._model_name = model or settings.embedding.gemini.model
        self._client = genai.Client(api_key=self._api_key)

    def embed_text(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model_name,
            contents=text,
        )
        return result.embeddings[0].values

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=self._model_name,
            contents=documents,
        )
        return [e.values for e in result.embeddings]
