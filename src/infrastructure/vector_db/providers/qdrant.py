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
            sparse_vectors_config={
                "sparse": qdrant_models.SparseVectorParams()
            }
        )
        logger.info("Created collection '%s' (size=%s, distance=%s) with sparse vector config", collection_name, vector_size, distance)

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
        points = []
        for record in records:
            if isinstance(record.vector, dict):
                vector_data = {}
                for name, vec in record.vector.items():
                    if name == "sparse":
                        if isinstance(vec, dict):
                            vector_data[name] = qdrant_models.SparseVector(
                                indices=vec["indices"], values=vec["values"]
                            )
                        elif hasattr(vec, "indices") and hasattr(vec, "values"):
                            vector_data[name] = qdrant_models.SparseVector(
                                indices=list(vec.indices), values=list(vec.values)
                            )
                        else:
                            vector_data[name] = vec
                    else:
                        vector_data[name] = vec
            else:
                vector_data = record.vector

            points.append(
                qdrant_models.PointStruct(
                    id=record.id,
                    vector=vector_data,
                    payload=record.payload,
                )
            )
        self._upsert_points(collection_name, points)

    def upsert_one(self, collection_name: str, record: VectorRecord) -> None:
        self.upsert(collection_name, [record])


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
        query_properties: list[str] | None = None,
    ) -> list[SearchResult]:
        # If alpha is 1.0 (pure vector search), bypass sparse vector search entirely
        if alpha == 1.0:
            return self.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                filter=filter,
            )

        # Lazy initialize fastembed sparse model
        if not hasattr(self, "_sparse_model"):
            from fastembed import SparseTextEmbedding
            self._sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

        # Generate sparse vector for query_text
        sparse_vecs = list(self._sparse_model.embed([query_text]))
        if not sparse_vecs:
            # Fall back to dense vector search if no sparse vector generated
            return self.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                filter=filter,
            )

        sparse_vec = sparse_vecs[0]
        qdrant_sparse_vector = qdrant_models.SparseVector(
            indices=list(sparse_vec.indices),
            values=list(sparse_vec.values)
        )

        # Query Qdrant using native Prefetch and Fusion (RRF)
        result = self._client.query_points(
            collection_name=collection_name,
            prefetch=[
                qdrant_models.Prefetch(
                    query=query_vector,
                    using="",
                    limit=limit * 3,
                ),
                qdrant_models.Prefetch(
                    query=qdrant_sparse_vector,
                    using="sparse",
                    limit=limit * 3,
                )
            ],
            query=qdrant_models.FusionQuery(
                fusion=qdrant_models.Fusion.RRF
            ),
            limit=limit,
            query_filter=self._to_qdrant_filter(filter),
        )

        return [
            SearchResult(
                id=point.id,
                score=point.score,
                payload=point.payload or {},
            )
            for point in result.points
        ]



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