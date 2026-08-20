import time
import uuid

import pytest

from src.infrastructure.vector_db.interface import (
    Filter,
    VectorRecord,
)
from src.infrastructure.vector_db.providers.weaviate import WeaviateDB

pytestmark = pytest.mark.integration

TEST_COLLECTION_PREFIX = "TestRayaShop"
VECTOR_SIZE = 8
SEARCH_SETTLE_SECONDS = 1.0


def wait_for_search(
    db: WeaviateDB,
    collection_name: str,
    query_vector: list[float],
    limit: int,
    min_results: int,
    *,
    timeout: float = 10.0,
) -> list:
    """Poll near-vector search until WCD finishes indexing the inserted objects."""
    deadline = time.monotonic() + timeout
    while True:
        results = db.search(collection_name, query_vector=query_vector, limit=limit)
        if len(results) >= min_results:
            return results
        if time.monotonic() >= deadline:
            return results
        time.sleep(0.5)


@pytest.fixture(scope="module")
def weaviate_db():
    db = WeaviateDB()
    _remove_test_collections(db)
    yield db
    _remove_test_collections(db)
    db.close()


def _remove_test_collections(db: WeaviateDB) -> None:
    for name in db.list_collections():
        if name.startswith(TEST_COLLECTION_PREFIX):
            db.delete_collection(name)


@pytest.fixture
def collection_name():
    return f"{TEST_COLLECTION_PREFIX}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_records():
    return [
        VectorRecord(
            id=str(uuid.uuid4()),
            vector=[float(i + 1)] * VECTOR_SIZE,
            payload={"text": f"Document {i}", "category": "test"},
        )
        for i in range(5)
    ]


class TestPing:
    def test_ping(self, weaviate_db):
        assert weaviate_db.ping() is True


class TestCollectionLifecycle:
    def test_create_and_list(self, weaviate_db, collection_name):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        collections = weaviate_db.list_collections()
        assert collection_name in collections
        weaviate_db.delete_collection(collection_name)

    def test_collection_exists(self, weaviate_db, collection_name):
        assert weaviate_db.collection_exists(collection_name) is False
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        assert weaviate_db.collection_exists(collection_name) is True
        weaviate_db.delete_collection(collection_name)

    def test_ensure_collection(self, weaviate_db, collection_name):
        created = weaviate_db.ensure_collection(collection_name, vector_size=VECTOR_SIZE)
        assert created is True
        created_again = weaviate_db.ensure_collection(collection_name, vector_size=VECTOR_SIZE)
        assert created_again is False
        weaviate_db.delete_collection(collection_name)

    def test_delete_nonexistent(self, weaviate_db):
        weaviate_db.delete_collection("NonexistentCollectionXyz")


class TestVectorOperations:
    def test_upsert_and_search(self, weaviate_db, collection_name, sample_records):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
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
            weaviate_db.delete_collection(collection_name)

    def test_upsert_one_and_retrieve(self, weaviate_db, collection_name):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            record_id = str(uuid.uuid4())
            record = VectorRecord(
                id=record_id,
                vector=[1.0] * VECTOR_SIZE,
                payload={"text": "Single document", "category": "test"},
            )
            weaviate_db.upsert_one(collection_name, record)
            results = weaviate_db.retrieve(collection_name, [record_id])
            assert len(results) == 1
            assert results[0].id == record_id
            assert results[0].payload["text"] == "Single document"
        finally:
            weaviate_db.delete_collection(collection_name)

    def test_delete_points(self, weaviate_db, collection_name):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            id1 = str(uuid.uuid4())
            id2 = str(uuid.uuid4())
            id3 = str(uuid.uuid4())
            records = [
                VectorRecord(id=id1, vector=[1.0] * VECTOR_SIZE, payload={"text": "Doc 1"}),
                VectorRecord(id=id2, vector=[2.0] * VECTOR_SIZE, payload={"text": "Doc 2"}),
                VectorRecord(id=id3, vector=[3.0] * VECTOR_SIZE, payload={"text": "Doc 3"}),
            ]
            weaviate_db.upsert(collection_name, records)
            count_before = weaviate_db.count(collection_name)
            assert count_before == 3
            weaviate_db.delete_points(collection_name, ids=[id1, id2])
            count_after = weaviate_db.count(collection_name)
            assert count_after == 1
        finally:
            weaviate_db.delete_collection(collection_name)

    def test_count(self, weaviate_db, collection_name, sample_records):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            weaviate_db.upsert(collection_name, sample_records)
            count = weaviate_db.count(collection_name)
            assert count == 5
        finally:
            weaviate_db.delete_collection(collection_name)

    def test_search_with_filter(self, weaviate_db, collection_name):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            records = [
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "books"}),
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
            ]
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
            assert len(results) == 2
            assert all(r.payload["category"] == "electronics" for r in results)
        finally:
            weaviate_db.delete_collection(collection_name)


class TestFullLifecycle:
    def test_full_lifecycle(self, weaviate_db, collection_name):
        weaviate_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            id1 = str(uuid.uuid4())
            id2 = str(uuid.uuid4())
            id3 = str(uuid.uuid4())
            records = [
                VectorRecord(id=id1, vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], payload={"name": "Product 1"}),
                VectorRecord(id=id2, vector=[0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1], payload={"name": "Product 2"}),
                VectorRecord(id=id3, vector=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], payload={"name": "Product 3"}),
            ]
            weaviate_db.upsert(collection_name, records)

            assert weaviate_db.count(collection_name) == 3
            results = wait_for_search(
                weaviate_db,
                collection_name,
                query_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                limit=2,
                min_results=1,
            )
            assert len(results) == 2
            assert results[0].id == id1
            retrieved = weaviate_db.retrieve(collection_name, [id1, id3])
            assert len(retrieved) == 2
            weaviate_db.delete_points(collection_name, ids=[id2])
            assert weaviate_db.count(collection_name) == 2
        finally:
            weaviate_db.delete_collection(collection_name)
            assert weaviate_db.collection_exists(collection_name) is False