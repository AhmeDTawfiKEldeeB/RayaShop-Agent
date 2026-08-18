from pydantic import BaseModel
from pydantic_settings import BaseSettings


class QdrantSettings(BaseModel):
    url: str = "http://localhost:6333"
    api_key: str = ""
    prefer_grpc: bool = False
    timeout: float = 10.0


class Settings(BaseSettings):
    # Application
    app_name: str = "RayaShop Agent"
    app_env: str = "development"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Vector Database
    vector_db_provider: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_prefer_grpc: bool = False
    qdrant_timeout: float = 10.0
    qdrant_collection_name: str = "rayashop"

    # Embeddings
    embedding_provider: str = "huggingface"
    huggingface_model_name: str = "all-MiniLM-L6-v2"
    gemini_api_key: str = ""
    gemini_model: str = "models/text-embedding-004"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def get_qdrant_settings() -> QdrantSettings:
    return QdrantSettings(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        prefer_grpc=settings.qdrant_prefer_grpc,
        timeout=settings.qdrant_timeout,
    )
