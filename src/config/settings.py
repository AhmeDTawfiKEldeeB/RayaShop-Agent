from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    name: str = Field(default="RayaShop Agent", description="Application name")
    env: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Enable debug mode")


class APISettings(BaseModel):
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")


class PostgresSettings(BaseModel):
    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="rayashop", description="Database name")
    user: str = Field(default="rayashop_user", description="Database user")
    password: str = Field(default="rayashop_password", description="Database password")
    sslmode: str = Field(default="require", description="SSL mode")

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.sslmode}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?ssl={self.sslmode}"


class QdrantSettings(BaseModel):
    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key: str | None = Field(default=None, description="Qdrant API key")
    collection_name: str = Field(default="rayashop", description="Default collection name")
    vector_size: int = Field(default=384, description="Vector dimension size")
    distance_metric: str = Field(default="cosine", description="Distance metric")
    prefer_grpc: bool = Field(default=False, description="Use gRPC protocol")
    timeout: float = Field(default=10.0, description="Request timeout in seconds")


class HuggingFaceSettings(BaseModel):
    model_name: str = Field(default="all-MiniLM-L6-v2", description="Hugging Face model name")


class GeminiSettings(BaseModel):
    api_key: str | None = Field(default=None, description="Gemini API key")
    model: str = Field(default="models/text-embedding-004", description="Gemini embedding model")


class EmbeddingSettings(BaseModel):
    provider: str = Field(default="huggingface", description="Embedding provider")
    huggingface: HuggingFaceSettings = HuggingFaceSettings()
    gemini: GeminiSettings = GeminiSettings()


class RayaScraperSettings(BaseModel):
    base_url: str = Field(
        default="https://www.rayashop.com",
        description="Raya website base URL",
    )

    api_url: str = Field(
        default="https://api-rayashop.global.ssl.fastly.net/graphql",
        description="Raya GraphQL API URL",
    )

    store_code: str = Field(
        default="en",
        description="Raya store code",
    )

    page_size: int = Field(
        default=20,
        description="Number of products per API page",
    )

class ScraperSettings(BaseModel):
    provider: str = Field(default="raya", description="Scraper provider")
    raya: RayaScraperSettings = RayaScraperSettings()


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    api: APISettings = APISettings()
    postgres: PostgresSettings = PostgresSettings()
    vector_db_provider: str = Field(default="qdrant", description="Vector DB provider")
    qdrant: QdrantSettings = QdrantSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    scraper: ScraperSettings = ScraperSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
