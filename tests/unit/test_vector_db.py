from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.http import models as qdrant_models

from src.infrastructure.vector_db.interface import (
    Distance,
    Filter,
    SearchResult,
    StoredRecord,
    VectorRecord,
)
from src.infrastructure.vector_db.providers.qdrant import QdrantDB


@pytest.fixture
def mock_client():
    with patch("src.infrastructure.vector_db.providers.qdrant.QdrantClient") as mock:
        client = mock.return_value
        client.get_collections.return_value = MagicMock(collections=[])
        client.collection_exists.return_value = False
        yield client


@pytest.fixture
def qdrant_db(mock_client):
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.qdrant.url = "http://localhost:6333"
        mock_settings.qdrant.api_key = None
        mock_settings.qdrant.prefer_grpc = False
        mock_settings.qdrant.timeout = 10.0
        db = QdrantDB()
        db._client = mock_client
        return db


class TestPing:
    def test_ping_success(self, qdrant_db, mock_client):
        mock_client.get_collections.return_value = MagicMock(collections=[])
        assert qdrant_db.ping() is True

    def test_ping_failure(self, qdrant_db, mock_client):
        mock_client.get_collections.side_effect = Exception("Connection refused")
        assert qdrant_db.ping() is False


class TestCollectionOperations:
    def test_collection_exists(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = True
        assert qdrant_db.collection_exists("test_collection") is True
        mock_client.collection_exists.assert_called_once_with("test_collection")

    def test_create_collection(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = False
        qdrant_db.create_collection("test_collection", vector_size=384)
        mock_client.create_collection.assert_called_once()
        call_kwargs = mock_client.create_collection.call_args
        assert call_kwargs.kwargs["collection_name"] == "test_collection"
        assert call_kwargs.kwargs["vectors_config"].size == 384

    def test_create_collection_already_exists(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = True
        qdrant_db.create_collection("existing_collection", vector_size=384)
        mock_client.create_collection.assert_not_called()

    def test_ensure_collection_new(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = False
        result = qdrant_db.ensure_collection("new_collection", vector_size=384)
        assert result is True
        mock_client.create_collection.assert_called_once()

    def test_ensure_collection_exists(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = True
        result = qdrant_db.ensure_collection("existing_collection", vector_size=384)
        assert result is False
        mock_client.create_collection.assert_not_called()

    def test_delete_collection(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = True
        qdrant_db.delete_collection("test_collection")
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_not_exists(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = False
        qdrant_db.delete_collection("nonexistent_collection")
        mock_client.delete_collection.assert_not_called()

    def test_list_collections(self, qdrant_db, mock_client):
        col1 = MagicMock()
        col1.name = "collection_1"
        col2 = MagicMock()
        col2.name = "collection_2"
        mock_client.get_collections.return_value = MagicMock(collections=[col1, col2])
        result = qdrant_db.list_collections()
        assert result == ["collection_1", "collection_2"]


class TestUpsertOperations:
    def test_upsert_records(self, qdrant_db, mock_client):
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], payload={"name": "test1"}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], payload={"name": "test2"}),
        ]
        qdrant_db.upsert("test_collection", records)
        mock_client.upsert.assert_called_once()
        call_kwargs = mock_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        assert len(call_kwargs["points"]) == 2
        assert call_kwargs["points"][0].id == "1"
        assert call_kwargs["points"][0].vector == [0.1, 0.2, 0.3]

    def test_upsert_one(self, qdrant_db, mock_client):
        record = VectorRecord(id="1", vector=[0.1, 0.2], payload={"name": "test"})
        qdrant_db.upsert_one("test_collection", record)
        mock_client.upsert.assert_called_once()
        call_kwargs = mock_client.upsert.call_args.kwargs
        assert len(call_kwargs["points"]) == 1

    def test_upsert_empty(self, qdrant_db, mock_client):
        qdrant_db.upsert("test_collection", [])
        mock_client.upsert.assert_not_called()

    def test_upsert_many_batching(self, qdrant_db, mock_client):
        records = [VectorRecord(id=str(i), vector=[0.1] * 3) for i in range(10)]
        qdrant_db.upsert_many("test_collection", records, batch_size=3)
        assert mock_client.upsert.call_count == 4


class TestSearchOperations:
    def test_search_returns_results(self, qdrant_db, mock_client):
        point1 = MagicMock(id="1", score=0.95, payload={"name": "test1"})
        point2 = MagicMock(id="2", score=0.85, payload={"name": "test2"})
        mock_client.query_points.return_value = MagicMock(points=[point1, point2])
        results = qdrant_db.search("test_collection", [0.1, 0.2], limit=5)
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].id == "1"
        assert results[0].score == 0.95
        assert results[0].payload == {"name": "test1"}

    def test_search_empty(self, qdrant_db, mock_client):
        mock_client.query_points.return_value = MagicMock(points=[])
        results = qdrant_db.search("test_collection", [0.1, 0.2])
        assert results == []

    def test_search_with_filter(self, qdrant_db, mock_client):
        mock_client.query_points.return_value = MagicMock(points=[])
        filter_obj = Filter(must=[{"field": "category", "match": "electronics"}])
        qdrant_db.search("test_collection", [0.1], filter=filter_obj)
        mock_client.query_points.assert_called_once()
        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs["query_filter"] is not None


class TestRetrieveOperations:
    def test_retrieve_records(self, qdrant_db, mock_client):
        rec1 = MagicMock(id="1", payload={"name": "test1"})
        rec2 = MagicMock(id="2", payload={"name": "test2"})
        mock_client.retrieve.return_value = [rec1, rec2]
        results = qdrant_db.retrieve("test_collection", ["1", "2"])
        assert len(results) == 2
        assert isinstance(results[0], StoredRecord)
        assert results[0].id == "1"

    def test_retrieve_empty_ids(self, qdrant_db, mock_client):
        results = qdrant_db.retrieve("test_collection", [])
        assert results == []
        mock_client.retrieve.assert_not_called()


class TestDeleteOperations:
    def test_delete_points_by_ids(self, qdrant_db, mock_client):
        qdrant_db.delete_points("test_collection", ids=["1", "2"])
        mock_client.delete.assert_called_once()
        call_kwargs = mock_client.delete.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        assert call_kwargs["points_selector"] == ["1", "2"]

    def test_delete_points_by_filter(self, qdrant_db, mock_client):
        filter_obj = Filter(must=[{"field": "status", "match": "deleted"}])
        qdrant_db.delete_points("test_collection", filter=filter_obj)
        mock_client.delete.assert_called_once()
        call_kwargs = mock_client.delete.call_args.kwargs
        assert call_kwargs["points_selector"] is not None

    def test_delete_points_no_ids_no_filter(self, qdrant_db, mock_client):
        qdrant_db.delete_points("test_collection")
        mock_client.delete.assert_not_called()


class TestCountOperations:
    def test_count(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = True
        mock_client.count.return_value = MagicMock(count=42)
        result = qdrant_db.count("test_collection")
        assert result == 42

    def test_count_nonexistent_collection(self, qdrant_db, mock_client):
        mock_client.collection_exists.return_value = False
        result = qdrant_db.count("nonexistent_collection")
        assert result == 0


class TestFactory:
    def test_factory_create_qdrant(self):
        from src.infrastructure.vector_db.factory import VectorDBFactory

        with patch("src.infrastructure.vector_db.providers.qdrant.QdrantClient"):
            with patch("src.config.settings.settings") as mock_settings:
                mock_settings.qdrant.url = "http://localhost:6333"
                mock_settings.qdrant.api_key = None
                mock_settings.qdrant.prefer_grpc = False
                mock_settings.qdrant.timeout = 10.0
                db = VectorDBFactory.create("qdrant")
                assert isinstance(db, QdrantDB)

    def test_factory_unknown_provider(self):
        from src.infrastructure.vector_db.factory import VectorDBFactory

        with pytest.raises(ValueError, match="Unknown vector DB provider"):
            VectorDBFactory.create("unknown_provider")
