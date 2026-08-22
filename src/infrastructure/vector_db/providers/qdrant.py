import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from src.config.settings import settings
from src.infrastructure.vector_db.interface import (
    Distance,
    Filter,
    SearchResult,
    StoredRecord,
    VectorRecord,
    VectorStore,
)

logger = logging.getLogger(__name__)

_DISTANCE_MAP = {
    Distance.COSINE: qdrant_models.Distance.COSINE,
    Distance.DOT: qdrant_models.Distance.DOT,
    Distance.EUCLID: qdrant_models.Distance.EUCLID,
}


class QdrantDB(VectorStore):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.url = url or settings.qdrant.url
        self.api_key = api_key or settings.qdrant.api_key
        self._client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            prefer_grpc=settings.qdrant.prefer_grpc,
            timeout=settings.qdrant.timeout,
        )

    @property
    def client(self) -> QdrantClient:
        return self._client

    def ping(self, timeout: float = 5.0) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Qdrant is unreachable: %s", exc)
            return False

    def collection_exists(self, collection_name: str) -> bool:
        return self._client.collection_exists(collection_name)

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        if self.collection_exists(collection_name):
            logger.info("Collection '%s' already exists, skipping creation", collection_name)
            return
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=vector_size, distance=_DISTANCE_MAP[distance]
            ),
        )
        logger.info("Created collection '%s' (size=%s, distance=%s)", collection_name, vector_size, distance)

    def ensure_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> bool:
        if self.collection_exists(collection_name):
            return False
        self.create_collection(collection_name, vector_size, distance)
        return True

    def delete_collection(self, collection_name: str) -> None:
        if not self.collection_exists(collection_name):
            logger.info("Collection '%s' does not exist, nothing to delete", collection_name)
            return
        self._client.delete_collection(collection_name)
        logger.info("Deleted collection '%s'", collection_name)

    def upsert(self, collection_name: str, records: list[VectorRecord]) -> None:
        points = [
            qdrant_models.PointStruct(
                id=record.id,
                vector=record.vector,
                payload=record.payload,
            )
            for record in records
        ]
        self._upsert_points(collection_name, points)

    def upsert_one(self, collection_name: str, record: VectorRecord) -> None:
        self._upsert_points(
            collection_name,
            [
                qdrant_models.PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload=record.payload,
                )
            ],
        )

    def upsert_many(
        self,
        collection_name: str,
        records: list[VectorRecord],
        batch_size: int = 64,
    ) -> None:
        for start in range(0, len(records), batch_size):
            self.upsert(collection_name, records[start : start + batch_size])

    def _upsert_points(self, collection_name: str, points: list[qdrant_models.PointStruct]) -> None:
        if not points:
            return
        self._client.upsert(collection_name=collection_name, points=points, wait=True)
        logger.debug("Upserted %s point(s) into '%s'", len(points), collection_name)

    @staticmethod
    def _to_qdrant_filter(filter: Filter | None) -> qdrant_models.Filter | None:
        if filter is None:
            return None
        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key=condition["field"],
                    match=qdrant_models.MatchValue(value=condition["match"]),
                )
                for condition in filter.must
            ]
        )

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter: Filter | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        result = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=self._to_qdrant_filter(filter),
            score_threshold=score_threshold,
        )
        return [
            SearchResult(
                id=point.id,
                score=point.score,
                payload=point.payload or {},
            )
            for point in result.points
        ]

    def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_vector: list[float],
        limit: int = 10,
        alpha: float = 0.5,
        filter: Filter | None = None,
    ) -> list[SearchResult]:
        logger.warning(
            "Qdrant does not support keyword fusion without a text index, "
            "falling back to semantic search for query=%r",
            query_text,
        )
        return self.search(collection_name, query_vector=query_vector, limit=limit, filter=filter)

    def retrieve(
        self,
        collection_name: str,
        ids: list[str | int],
    ) -> list[StoredRecord]:
        if not ids:
            return []
        records = self._client.retrieve(collection_name=collection_name, ids=ids)
        return [
            StoredRecord(
                id=record.id,
                payload=record.payload or {},
            )
            for record in records
        ]

    def delete_points(
        self,
        collection_name: str,
        ids: list[str | int] | None = None,
        filter: Filter | None = None,
    ) -> None:
        if ids is not None and ids:
            self._client.delete(collection_name=collection_name, points_selector=ids, wait=True)
        elif filter is not None:
            self._client.delete(
                collection_name=collection_name,
                points_selector=self._to_qdrant_filter(filter),
                wait=True,
            )
        else:
            logger.warning("No ids or filter provided, skipping delete for '%s'", collection_name)

    def count(
        self,
        collection_name: str,
        filter: Filter | None = None,
        exact: bool = True,
    ) -> int:
        if not self.collection_exists(collection_name):
            return 0
        result = self._client.count(
            collection_name=collection_name,
            count_filter=self._to_qdrant_filter(filter),
            exact=exact,
        )
        return result.count

    def list_collections(self) -> list[str]:
        response = self._client.get_collections()
        return [collection.name for collection in response.collections]

    def close(self) -> None:
        self._client.close()