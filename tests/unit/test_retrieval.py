"""Unit tests for the retrieval node and retrieval tool."""

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.Agent.nodes.retrieval import _get_latest_user_message, retrieval_node
from src.Agent.tools.retrieval_tool import format_search_results, search_products_raw

# --------------------------------------------------------------------------- _get_latest_user_message


class TestGetLatestUserMessage:
    def test_finds_last_human_message(self):
        msgs = [
            HumanMessage(content="first"),
            AIMessage(content="reply"),
            HumanMessage(content="second"),
        ]
        result = _get_latest_user_message({"messages": msgs})
        assert result.content == "second"

    def test_returns_none_when_no_human(self):
        msgs = [AIMessage(content="only ai"), SystemMessage(content="sys")]
        result = _get_latest_user_message({"messages": msgs})
        assert result is None

    def test_returns_none_for_empty_messages(self):
        result = _get_latest_user_message({"messages": []})
        assert result is None

    def test_single_human_message(self):
        msgs = [HumanMessage(content="only")]
        result = _get_latest_user_message({"messages": msgs})
        assert result.content == "only"


# --------------------------------------------------------------------------- retrieval_node


class TestRetrievalNode:
    def test_calls_search_with_query(self):
        state = {"messages": [HumanMessage(content="samsung phone")]}
        fake_results = [{"name": "Galaxy S24", "price": 35000}]

        with patch("src.Agent.nodes.retrieval.search_products_raw", return_value=fake_results) as mock_search:
            result = retrieval_node(state)

        mock_search.assert_called_once_with(query="samsung phone", limit=7)
        assert result["search_results"] == fake_results

    def test_returns_empty_when_no_human_message(self):
        state = {"messages": [AIMessage(content="ai only")]}
        result = retrieval_node(state)
        assert result["search_results"] == []

    def test_returns_empty_for_empty_messages(self):
        state = {"messages": []}
        result = retrieval_node(state)
        assert result["search_results"] == []

    def test_strips_whitespace_from_query(self):
        state = {"messages": [HumanMessage(content="  samsung phone  ")]}

        with patch("src.Agent.nodes.retrieval.search_products_raw", return_value=[]) as mock_search:
            retrieval_node(state)

        mock_search.assert_called_once_with(query="samsung phone", limit=7)

    def test_returns_empty_for_whitespace_only_query(self):
        state = {"messages": [HumanMessage(content="   ")]}

        with patch("src.Agent.nodes.retrieval.search_products_raw") as mock_search:
            result = retrieval_node(state)

        mock_search.assert_not_called()
        assert result["search_results"] == []


# --------------------------------------------------------------------------- search_products_raw


class TestSearchProductsRaw:
    def test_empty_query_returns_empty(self):
        result = search_products_raw("")
        assert result == []

    def test_whitespace_query_returns_empty(self):
        result = search_products_raw("   ")
        assert result == []

    def test_formats_results_from_store(self):
        mock_result = MagicMock()
        mock_result.payload = {
            "product_id": "p1",
            "name": "iPhone 15",
            "sku": "APL-15",
            "brand": "Apple",
            "category": "Phones",
            "description": "Apple iPhone 15",
            "short_description": "iPhone 15",
            "attributes": {"color": "black"},
            "price": 50000,
            "old_price": 55000,
            "stock_status": "In Stock",
            "url": "https://rayashop.com/iphone15",
            "thumbnail": "https://img/iphone15.jpg",
        }
        mock_result.score = 0.8765

        mock_store = MagicMock()
        mock_store.db.hybrid_search.return_value = [mock_result]
        mock_store.collection_name = "RayaShopProduct"

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 384

        with (
            patch("src.Agent.tools.retrieval_tool._get_store", return_value=mock_store),
            patch("src.Agent.tools.retrieval_tool._get_embedder", return_value=mock_embedder),
        ):
            results = search_products_raw("iphone 15", limit=5)

        assert len(results) == 1
        p = results[0]
        assert p["id"] == "p1"
        assert p["name"] == "iPhone 15"
        assert p["sku"] == "APL-15"
        assert p["brand"] == "Apple"
        assert p["category"] == "Phones"
        assert p["price"] == 50000
        assert p["old_price"] == 55000
        assert p["stock_status"] == "In Stock"
        assert p["score"] == 0.8765

    def test_passes_limit_to_hybrid_search(self):
        mock_store = MagicMock()
        mock_store.db.hybrid_search.return_value = []
        mock_store.collection_name = "RayaShopProduct"

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 384

        with (
            patch("src.Agent.tools.retrieval_tool._get_store", return_value=mock_store),
            patch("src.Agent.tools.retrieval_tool._get_embedder", return_value=mock_embedder),
        ):
            search_products_raw("phone", limit=3)

        call_kwargs = mock_store.db.hybrid_search.call_args
        assert call_kwargs[1]["limit"] == 3

    def test_handles_empty_payload_fields(self):
        mock_result = MagicMock()
        mock_result.payload = {}
        mock_result.score = 0.5

        mock_store = MagicMock()
        mock_store.db.hybrid_search.return_value = [mock_result]
        mock_store.collection_name = "RayaShopProduct"

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 384

        with (
            patch("src.Agent.tools.retrieval_tool._get_store", return_value=mock_store),
            patch("src.Agent.tools.retrieval_tool._get_embedder", return_value=mock_embedder),
        ):
            results = search_products_raw("phone")

        p = results[0]
        assert p["id"] is None
        assert p["name"] == ""
        assert p["price"] == 0
        assert p["brand"] == ""

    def test_handles_none_payload(self):
        mock_result = MagicMock()
        mock_result.payload = None
        mock_result.score = 0.3

        mock_store = MagicMock()
        mock_store.db.hybrid_search.return_value = [mock_result]
        mock_store.collection_name = "RayaShopProduct"

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 384

        with (
            patch("src.Agent.tools.retrieval_tool._get_store", return_value=mock_store),
            patch("src.Agent.tools.retrieval_tool._get_embedder", return_value=mock_embedder),
        ):
            results = search_products_raw("phone")

        p = results[0]
        assert p["id"] is None
        assert p["name"] == ""

    def test_embeds_query_before_search(self):
        mock_store = MagicMock()
        mock_store.db.hybrid_search.return_value = []
        mock_store.collection_name = "RayaShopProduct"

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.2] * 384

        with (
            patch("src.Agent.tools.retrieval_tool._get_store", return_value=mock_store),
            patch("src.Agent.tools.retrieval_tool._get_embedder", return_value=mock_embedder),
        ):
            search_products_raw("laptop")

        mock_embedder.embed_text.assert_called_once_with("laptop")
        mock_store.db.hybrid_search.assert_called_once()


# --------------------------------------------------------------------------- format_search_results


class TestFormatSearchResults:
    def test_serializes_to_json(self):
        products = [{"name": "iPhone", "price": 50000}]
        result = format_search_results(products)
        parsed = json.loads(result)
        assert parsed == products

    def test_empty_list(self):
        assert format_search_results([]) == "[]"

    def test_preserves_unicode(self):
        products = [{"name": "موبايل سامسونج"}]
        result = format_search_results(products)
        assert "موبايل سامسونج" in result
