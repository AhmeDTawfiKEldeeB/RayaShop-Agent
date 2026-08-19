import uuid

import pytest

from src.infrastructure.vector_db.interface import (
    Distance,
    Filter,
    VectorRecord,
)
from src.infrastructure.vector_db.providers.qdrant import QdrantDB

pytestmark = pytest.mark.integration

TEST_COLLECTION_PREFIX = "test_rayashop"
VECTOR_SIZE = 8


@pytest.fixture(scope="module")
def qdrant_db():
    db = QdrantDB(url="http://localhost:6333")
    yield db
    db.close()


@pytest.fixture
def collection_name():
    return f"{TEST_COLLECTION_PREFIX}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_records():
    return [
        VectorRecord(
            id=str(uuid.uuid4()),
            vector=[float(i)] * VECTOR_SIZE,
            payload={"text": f"Document {i}", "category": "test"},
        )
        for i in range(5)
    ]


class TestPing:
    def test_ping(self, qdrant_db):
        assert qdrant_db.ping() is True


class TestCollectionLifecycle:
    def test_create_and_list(self, qdrant_db, collection_name):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        collections = qdrant_db.list_collections()
        assert collection_name in collections
        qdrant_db.delete_collection(collection_name)

    def test_collection_exists(self, qdrant_db, collection_name):
        assert qdrant_db.collection_exists(collection_name) is False
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        assert qdrant_db.collection_exists(collection_name) is True
        qdrant_db.delete_collection(collection_name)

    def test_ensure_collection(self, qdrant_db, collection_name):
        created = qdrant_db.ensure_collection(collection_name, vector_size=VECTOR_SIZE)
        assert created is True
        created_again = qdrant_db.ensure_collection(collection_name, vector_size=VECTOR_SIZE)
        assert created_again is False
        qdrant_db.delete_collection(collection_name)

    def test_delete_nonexistent(self, qdrant_db):
        qdrant_db.delete_collection("nonexistent_collection_xyz")


class TestVectorOperations:
    def test_upsert_and_search(self, qdrant_db, collection_name, sample_records):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            qdrant_db.upsert(collection_name, sample_records)
            results = qdrant_db.search(
                collection_name,
                query_vector=[0.0] * VECTOR_SIZE,
                limit=3,
            )
            assert len(results) > 0
            assert results[0].score is not None
            assert "text" in results[0].payload
        finally:
            qdrant_db.delete_collection(collection_name)

    def test_upsert_one_and_retrieve(self, qdrant_db, collection_name):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            record_id = str(uuid.uuid4())
            record = VectorRecord(
                id=record_id,
                vector=[1.0] * VECTOR_SIZE,
                payload={"text": "Single document", "category": "test"},
            )
            qdrant_db.upsert_one(collection_name, record)
            results = qdrant_db.retrieve(collection_name, [record_id])
            assert len(results) == 1
            assert results[0].id == record_id
            assert results[0].payload["text"] == "Single document"
        finally:
            qdrant_db.delete_collection(collection_name)

    def test_delete_points(self, qdrant_db, collection_name):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            id1 = str(uuid.uuid4())
            id2 = str(uuid.uuid4())
            id3 = str(uuid.uuid4())
            records = [
                VectorRecord(id=id1, vector=[0.0] * VECTOR_SIZE, payload={"text": "Doc 1"}),
                VectorRecord(id=id2, vector=[1.0] * VECTOR_SIZE, payload={"text": "Doc 2"}),
                VectorRecord(id=id3, vector=[2.0] * VECTOR_SIZE, payload={"text": "Doc 3"}),
            ]
            qdrant_db.upsert(collection_name, records)
            count_before = qdrant_db.count(collection_name)
            assert count_before == 3
            qdrant_db.delete_points(collection_name, ids=[id1, id2])
            count_after = qdrant_db.count(collection_name)
            assert count_after == 1
        finally:
            qdrant_db.delete_collection(collection_name)

    def test_count(self, qdrant_db, collection_name, sample_records):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            qdrant_db.upsert(collection_name, sample_records)
            count = qdrant_db.count(collection_name)
            assert count == 5
        finally:
            qdrant_db.delete_collection(collection_name)

    def test_search_with_filter(self, qdrant_db, collection_name):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        try:
            records = [
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "books"}),
                VectorRecord(id=str(uuid.uuid4()), vector=[1.0] * VECTOR_SIZE, payload={"category": "electronics"}),
            ]
            qdrant_db.upsert(collection_name, records)
            filter_obj = Filter(must=[{"field": "category", "match": "electronics"}])
            results = qdrant_db.search(
                collection_name,
                query_vector=[1.0] * VECTOR_SIZE,
                limit=10,
                filter=filter_obj,
            )
            assert len(results) == 2
            assert all(r.payload["category"] == "electronics" for r in results)
        finally:
            qdrant_db.delete_collection(collection_name)


class TestFullLifecycle:
    def test_full_lifecycle(self, qdrant_db, collection_name):
        qdrant_db.create_collection(collection_name, vector_size=VECTOR_SIZE)
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        id3 = str(uuid.uuid4())
        records = [
            VectorRecord(id=id1, vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], payload={"name": "Product 1"}),
            VectorRecord(id=id2, vector=[0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1], payload={"name": "Product 2"}),
            VectorRecord(id=id3, vector=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], payload={"name": "Product 3"}),
        ]
        qdrant_db.upsert(collection_name, records)
        assert qdrant_db.count(collection_name) == 3
        results = qdrant_db.search(
            collection_name,
            query_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            limit=2,
        )
        assert len(results) == 2
        assert results[0].id == id1
        retrieved = qdrant_db.retrieve(collection_name, [id1, id3])
        assert len(retrieved) == 2
        qdrant_db.delete_points(collection_name, ids=[id2])
        assert qdrant_db.count(collection_name) == 2
        qdrant_db.delete_collection(collection_name)
        assert qdrant_db.collection_exists(collection_name) is False
