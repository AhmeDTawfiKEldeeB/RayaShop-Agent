import logging
import uuid

import weaviate
from weaviate.auth import AuthApiKey
from weaviate.collections.classes.config import Configure, VectorDistances
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.filters import Filter as WvFilter

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

ID_NAMESPACE = uuid.UUID("b6ed07fd-0afc-f762-2726-22ae493b4e4c")
ORIGINAL_ID_KEY = "_uid"

_DISTANCE_MAP = {
    Distance.COSINE: VectorDistances.COSINE,
    Distance.DOT: VectorDistances.DOT,
    Distance.EUCLID: VectorDistances.L2_SQUARED,
}


def _normalize_collection_name(name: str) -> str:
    if not name:
        return name
    return name[0].upper() + name[1:]


def _to_uuid(record_id: str | int) -> str:
    if isinstance(record_id, uuid.UUID):
        return str(record_id)
    text = str(record_id)
    try:
        parsed = uuid.UUID(text)
        return str(parsed)
    except ValueError:
        return str(uuid.uuid5(ID_NAMESPACE, text))


def _extract_result(
    object_, distance_metric: Distance
) -> tuple[str | int, float, dict]:
    properties = dict(object_.properties or {})
    original_id = str(properties.pop(ORIGINAL_ID_KEY, str(object_.uuid)))
    raw_distance = object_.metadata.distance if object_.metadata is not None else None
    if raw_distance is None:
        score = 0.0
    elif distance_metric in (Distance.COSINE, Distance.DOT):
        score = 1.0 - float(raw_distance)
    else:
        score = 1.0 / (1.0 + float(raw_distance))
    return original_id, score, properties


class WeaviateDB(VectorStore):
    def __init__(
        self,
        cloud_url: str | None = None,
        host: str | None = None,
        http_port: int | None = None,
        http_secure: bool | None = None,
        grpc_host: str | None = None,
        grpc_port: int | None = None,
        grpc_secure: bool | None = None,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        w = settings.weaviate

        self.cloud_url = cloud_url or (w.cloud_url.strip() if w.cloud_url else None)
        self.host = host or w.host
        self.http_port = http_port or w.http_port
        self.http_secure = http_secure if http_secure is not None else w.http_secure
        self.grpc_host = grpc_host or w.grpc_host or w.host
        self.grpc_port = grpc_port or w.grpc_port
        self.grpc_secure = grpc_secure if grpc_secure is not None else w.grpc_secure
        self.api_key = api_key if api_key is not None else w.api_key
        self.headers = headers if headers is not None else dict(w.headers)
        self.timeout = timeout or w.timeout
        self.skip_init_checks = w.skip_init_checks

        self._client: weaviate.WeaviateClient | None = None

    @property
    def client(self) -> weaviate.WeaviateClient:
        return self._connect()

    def _connect(self) -> weaviate.WeaviateClient:
        if self._client is not None and self._client.is_connected:
            return self._client

        auth_credentials = AuthApiKey(self.api_key) if self.api_key else None

        additional_config = weaviate.config.AdditionalConfig(
            timeout=weaviate.config.Timeout(
                query=self.timeout,
                insert=self.timeout,
                init=min(self.timeout, 2.0),
            ),
        )

        if self.cloud_url:
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cloud_url,
                auth_credentials=auth_credentials,
                headers=self.headers or None,
                additional_config=additional_config,
                skip_init_checks=self.skip_init_checks,
            )
        else:
            client = weaviate.connect_to_custom(
                http_host=self.host,
                http_port=self.http_port,
                http_secure=self.http_secure,
                grpc_host=self.grpc_host,
                grpc_port=self.grpc_port,
                grpc_secure=self.grpc_secure,
                headers=self.headers or None,
                additional_config=additional_config,
                auth_credentials=auth_credentials,
                skip_init_checks=self.skip_init_checks,
            )

        self._client = client
        return client

    def ping(self, timeout: float = 5.0) -> bool:
        try:
            client = self._connect()
            return bool(client.is_ready())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weaviate is unreachable: %s", exc)
            return False

    def collection_exists(self, collection_name: str) -> bool:
        return bool(
            self._connect().collections.exists(
                _normalize_collection_name(collection_name)
            )
        )

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        name = _normalize_collection_name(collection_name)
        if self.collection_exists(name):
            logger.info("Collection '%s' already exists, skipping creation", name)
            return

        self._connect().collections.create(
            name=name,
            vector_config=Configure.Vectors.self_provided(
                vector_index_config=Configure.VectorIndex.hfresh(
                    distance_metric=_DISTANCE_MAP[distance]
                )
            ),
        )
        logger.info(
            "Created collection '%s' (size=%s, distance=%s)",
            name,
            vector_size,
            distance,
        )

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
        name = _normalize_collection_name(collection_name)
        if not self.collection_exists(name):
            logger.info("Collection '%s' does not exist, nothing to delete", name)
            return
        self._connect().collections.delete(name)
        logger.info("Deleted collection '%s'", name)

    def _collection(self, collection_name: str):
        try:
            return self._connect().collections.get(
                _normalize_collection_name(collection_name)
            )
        except weaviate.exceptions.WeaviateConnectionError:
            raise ConnectionError("Weaviate is not connected") from None

    def upsert(self, collection_name: str, records: list[VectorRecord]) -> None:
        collection = self._collection(collection_name)

        objects = [
            DataObject(
                uuid=_to_uuid(record.id),
                vector=record.vector,
                properties={
                    **(record.payload or {}),
                    ORIGINAL_ID_KEY: record.id,
                },
            )
            for record in records
        ]
        if not objects:
            return

        collection.data.insert_many(objects)
        logger.debug("Upserted %s object(s) into '%s'", len(objects), collection_name)

    def upsert_one(self, collection_name: str, record: VectorRecord) -> None:
        self.upsert(collection_name, [record])

    def upsert_many(
        self,
        collection_name: str,
        records: list[VectorRecord],
        batch_size: int = 64,
    ) -> None:
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            collection = self._collection(collection_name)
            objects = [
                DataObject(
                    uuid=_to_uuid(record.id),
                    vector=record.vector,
                    properties={
                        **(record.payload or {}),
                        ORIGINAL_ID_KEY: record.id,
                    },
                )
                for record in batch
            ]
            if objects:
                collection.data.insert_many(objects)

    @staticmethod
    def _to_weaviate_filter(filter: Filter | None):
        if filter is None or not filter.must:
            return None
        clauses = [
            WvFilter.by_property(condition["field"]).equal(condition["match"])
            for condition in filter.must
        ]
        return WvFilter.all_of(clauses)

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter: Filter | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        distance_metric = self._distance_metric_for(collection_name)
        results = self._collection(collection_name).query.near_vector(
            near_vector=query_vector,
            limit=limit,
            filters=self._to_weaviate_filter(filter),
            distance=self._threshold_to_distance(score_threshold, distance_metric),
            return_metadata=["distance"],
        )

        return [
            SearchResult(
                id=record_id,
                score=score,
                payload=payload,
            )
            for object_ in results.objects
            for record_id, score, payload in [_extract_result(object_, distance_metric)]
        ]

    def retrieve(
        self,
        collection_name: str,
        ids: list[str | int],
    ) -> list[StoredRecord]:
        if not ids:
            return []

        distance_metric = self._distance_metric_for(collection_name)
        results = self._collection(collection_name).query.fetch_objects_by_ids(
            ids=[_to_uuid(record_id) for record_id in ids]
        )

        return [
            StoredRecord(
                id=record_id,
                payload=payload,
            )
            for object_ in results.objects
            for record_id, score, payload in [_extract_result(object_, distance_metric)]
        ]

    def delete_points(
        self,
        collection_name: str,
        ids: list[str | int] | None = None,
        filter: Filter | None = None,
    ) -> None:
        collection = self._collection(collection_name)

        if ids is not None and ids:
            for record_id in ids:
                collection.data.delete_by_id(_to_uuid(record_id))
        elif filter is not None and filter.must:
            collection.data.delete_many(where=self._to_weaviate_filter(filter))
        else:
            logger.warning(
                "No ids or filter provided, skipping delete for '%s'",
                collection_name,
            )

    def count(
        self,
        collection_name: str,
        filter: Filter | None = None,
        exact: bool = True,
    ) -> int:
        if not self.collection_exists(collection_name):
            return 0
        result = self._collection(collection_name).aggregate.over_all(
            total_count=True,
            filters=self._to_weaviate_filter(filter),
        )
        return result.total_count or 0

    def list_collections(self) -> list[str]:
        collections = self._connect().collections.list_all(simple=True)
        return list(collections.keys())

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Error closing Weaviate client: %s", exc)
            self._client = None

    def _distance_metric_for(self, collection_name: str) -> Distance:
        metric = settings.weaviate.distance_metric.lower()
        for distance in Distance:
            if distance.value == metric:
                return distance
        return Distance.COSINE

    @staticmethod
    def _threshold_to_distance(score_threshold: float | None, distance: Distance):
        if score_threshold is None:
            return None
        if distance in (Distance.COSINE, Distance.DOT):
            return 1.0 - score_threshold
        if distance == Distance.EUCLID:
            if score_threshold <= 0:
                return None
            return 1.0 / score_threshold - 1.0
        return None
