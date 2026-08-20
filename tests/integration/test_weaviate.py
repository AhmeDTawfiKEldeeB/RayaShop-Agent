import time
import uuid

import pytest

from src.config.settings import settings
from src.infrastructure.vector_db.interface import (
    Filter,
    VectorRecord,
)
from src.infrastructure.vector_db.providers.weaviate import WeaviateDB

pytestmark = pytest.mark.integration

VECTOR_SIZE = 8
TEST_MARKER = "_integration_test"


def wait_for_search(
    db: WeaviateDB,
    collection_name: str,
    query_vector: list[float],
    limit: int,
    min_results: int,
    *,
    timeout: float = 10.0,
) -> list:
    deadline = time.monotonic() + timeout
    while True:
        results = db.search(collection_name, query_vector=query_vector, limit=limit)
        if len(results) >= min_results:
            return results
        if time.monotonic() >= deadline:
            return results
        time.sleep(0.5)


def _make_test_id() -> str:
    return f"{TEST_MARKER}_{uuid.uuid4().hex[:8]}"


def _make_test_records(n: int) -> list[VectorRecord]:
    return [
        VectorRecord(
            id=_make_test_id(),
            vector=[float(i + 1)] * VECTOR_SIZE,
            payload={"text": f"Document {i}", "category": "test"},
        )
        for i in range(n)
    ]


def _cleanup_records(db: WeaviateDB, collection: str, ids: list[str]) -> None:
    if ids:
        db.delete_points(collection, ids=ids)


@pytest.fixture(scope="module")
def weaviate_db():
    db = WeaviateDB()
    assert db.ping(), "Weaviate must be reachable"
    yield db
    db.close()


@pytest.fixture(scope="module")
def collection_name():
    return settings.weaviate.product_collection_name


@pytest.fixture
def sample_records():
    return _make_test_records(5)


@pytest.fixture(autouse=True)
def _cleanup_after_test(weaviate_db, collection_name):
    yield
    weaviate_db.close()


class TestPing:
    def test_ping(self, weaviate_db):
        assert weaviate_db.ping() is True


class TestCollectionLifecycle:
    @pytest.mark.skip(reason="WCD free-tier allows only 1 collection")
    def test_create_and_list(self, weaviate_db, collection_name):
        pass

    @pytest.mark.skip(reason="WCD free-tier allows only 1 collection")
    def test_ensure_collection(self, weaviate_db, collection_name):
        pass

    def test_collection_exists(self, weaviate_db, collection_name):
        assert weaviate_db.collection_exists(collection_name) is True

    def test_delete_nonexistent(self, weaviate_db):
        weaviate_db.delete_collection("NonexistentCollectionXyz")

    def test_list_collections(self, weaviate_db):
        collections = weaviate_db.list_collections()
        assert settings.weaviate.product_collection_name in collections


class TestVectorOperations:
    def test_upsert_and_search(self, weaviate_db, collection_name, sample_records):
        ids = [r.id for r in sample_records]
        try:
            weaviate_db.upsert(collection_name, sample_records)
            results = wait_for_search(
                weaviate_db,
                collection_name,
                query_vector=[3.0] * VECTOR_SIZE,
                limit=3,
                min_results=1,
            )
            assert len(results) > 0
            assert results[0].score is not None
            assert "text" in results[0].payload
        finally:
            _cleanup_records(weaviate_db, collection_name, ids)

    def test_upsert_one_and_retrieve(self, weaviate_db, collection_name):
        record_id = _make_test_id()
        record = VectorRecord(
            id=record_id,
            vector=[1.0] * VECTOR_SIZE,
            payload={"text": "Single document", "category": "test"},
        )
        try:
            weaviate_db.upsert_one(collection_name, record)
            results = weaviate_db.retrieve(collection_name, [record_id])
            assert len(results) == 1
            assert results[0].id == record_id
            assert results[0].payload["text"] == "Single document"
        finally:
            _cleanup_records(weaviate_db, collection_name, [record_id])

    def test_delete_points(self, weaviate_db, collection_name):
        id1 = _make_test_id()
        id2 = _make_test_id()
        id3 = _make_test_id()
        records = [
            VectorRecord(id=id1, vector=[1.0] * VECTOR_SIZE, payload={"text": "Doc 1"}),
            VectorRecord(id=id2, vector=[2.0] * VECTOR_SIZE, payload={"text": "Doc 2"}),
            VectorRecord(id=id3, vector=[3.0] * VECTOR_SIZE, payload={"text": "Doc 3"}),
        ]
        try:
            weaviate_db.upsert(collection_name, records)
            weaviate_db.delete_points(collection_name, ids=[id1, id2])
            remaining = weaviate_db.retrieve(collection_name, [id3])
            assert len(remaining) == 1
            assert remaining[0].id == id3
        finally:
            _cleanup_records(weaviate_db, collection_name, [id3])

    def test_count(self, weaviate_db, collection_name, sample_records):
        ids = [r.id for r in sample_records]
        try:
            weaviate_db.upsert(collection_name, sample_records)
            count = weaviate_db.count(collection_name)
            assert count >= 5
        finally:
            _cleanup_records(weaviate_db, collection_name, ids)

    def test_search_with_filter(self, weaviate_db, collection_name):
        records = [
            VectorRecord(id=_make_test_id(), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
            VectorRecord(id=_make_test_id(), vector=[1.0] * VECTOR_SIZE, payload={"category": "books"}),
            VectorRecord(id=_make_test_id(), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
        ]
        ids = [r.id for r in records]
        try:
            weaviate_db.upsert(collection_name, records)
            wait_for_search(
                weaviate_db,
                collection_name,
                query_vector=[1.0] * VECTOR_SIZE,
                limit=10,
                min_results=3,
            )
            filter_obj = Filter(must=[{"field": "category", "match": "electronics"}])
            results = weaviate_db.search(
                collection_name,
                query_vector=[1.0] * VECTOR_SIZE,
                limit=10,
                filter=filter_obj,
            )
            assert len(results) >= 2
            assert all(r.payload["category"] == "electronics" for r in results)
        finally:
            _cleanup_records(weaviate_db, collection_name, ids)


class TestFullLifecycle:
    def test_full_lifecycle(self, weaviate_db, collection_name):
        id1 = _make_test_id()
        id2 = _make_test_id()
        id3 = _make_test_id()
        records = [
            VectorRecord(id=id1, vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], payload={"name": "Product 1"}),
            VectorRecord(id=id2, vector=[0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1], payload={"name": "Product 2"}),
            VectorRecord(id=id3, vector=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], payload={"name": "Product 3"}),
        ]
        try:
            weaviate_db.upsert(collection_name, records)
            results = wait_for_search(
                weaviate_db,
                collection_name,
                query_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                limit=2,
                min_results=1,
            )
            assert len(results) >= 1
            retrieved = weaviate_db.retrieve(collection_name, [id1, id3])
            assert len(retrieved) == 2
            weaviate_db.delete_points(collection_name, ids=[id2])
        finally:
            _cleanup_records(weaviate_db, collection_name, [id1, id3])
