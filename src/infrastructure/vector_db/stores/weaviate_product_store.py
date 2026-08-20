import logging

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    VectorDistances,
)

from src.config.settings import settings
from src.infrastructure.vector_db.interface import Distance
from src.infrastructure.vector_db.providers.weaviate import (
    _DISTANCE_MAP,
    WeaviateDB,
    _normalize_collection_name,
)

logger = logging.getLogger(__name__)

PRODUCT_PROPERTIES = [
    Property(name="product_id", data_type=DataType.INT),
    Property(name="name", data_type=DataType.TEXT),
    Property(name="sku", data_type=DataType.TEXT),
    Property(name="price", data_type=DataType.NUMBER),
    Property(name="old_price", data_type=DataType.NUMBER),
    Property(name="stock_status", data_type=DataType.TEXT),
    Property(name="url", data_type=DataType.TEXT),
    Property(name="thumbnail", data_type=DataType.TEXT),
]


def _resolve_distance() -> VectorDistances:
    metric = settings.weaviate.distance_metric.lower()
    for distance in Distance:
        if distance.value == metric:
            return _DISTANCE_MAP[distance]
    return VectorDistances.COSINE


class WeaviateProductStore:
    """Owns the RayaShopProduct collection inside the existing Weaviate client."""

    def __init__(self, db: WeaviateDB | None = None) -> None:
        self._db = db or WeaviateDB()
        self.collection_name = _normalize_collection_name(
            settings.weaviate.product_collection_name
        )

    @property
    def client(self) -> weaviate.WeaviateClient:
        return self._db.client

    @property
    def db(self) -> WeaviateDB:
        return self._db

    def ping(self, timeout: float = 5.0) -> bool:
        return self._db.ping(timeout=timeout)

    def collection_exists(self) -> bool:
        return self._db.collection_exists(self.collection_name)

    def create_collection(self) -> None:
        if self.collection_exists():
            logger.info("Collection '%s' already exists, skipping creation", self.collection_name)
            return

        distance = _resolve_distance()

        self.client.collections.create(
            name=self.collection_name,
            description="RayaShop product catalog with self-provided vectors",
            properties=PRODUCT_PROPERTIES,
            vector_config=Configure.Vectors.self_provided(
                vector_index_config=Configure.VectorIndex.hfresh(distance_metric=distance)
            ),
        )
        logger.info("Created collection '%s'", self.collection_name)

    def ensure_collection(self) -> bool:
        if self.collection_exists():
            return False
        self.create_collection()
        return True

    def close(self) -> None:
        self._db.close()