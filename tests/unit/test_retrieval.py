"""Unit tests for the retrieval node and retrieval tool."""

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.Agent.nodes.retrieval import (
    _get_latest_user_message,
    _is_followup_question,
    retrieval_node,
)
from src.Agent.tools.retrieval_tool import (
    _rerank,
    format_search_results,
    search_products_raw,
)

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

    def test_followup_keeps_existing_results(self):
        existing = [{"name": "Headphone", "price": 1000}]
        state = {
            "messages": [HumanMessage(content="what colors does it come in?")],
            "search_results": existing,
        }

        with patch("src.Agent.nodes.retrieval.search_products_raw") as mock_search:
            result = retrieval_node(state)

        mock_search.assert_not_called()
        assert result["search_results"] == existing

    def test_followup_arabic_keeps_existing_results(self):
        existing = [{"name": "تكييف", "price": 15000}]
        state = {
            "messages": [HumanMessage(content="لونه ايه؟")],
            "search_results": existing,
        }

        with patch("src.Agent.nodes.retrieval.search_products_raw") as mock_search:
            result = retrieval_node(state)

        mock_search.assert_not_called()
        assert result["search_results"] == existing

    def test_new_product_intent_still_searches(self):
        state = {
            "messages": [HumanMessage(content="do you have samsung phones?")],
            "search_results": [{"name": "old"}],
        }

        with patch("src.Agent.nodes.retrieval.search_products_raw", return_value=[]) as mock_search:
            retrieval_node(state)

        mock_search.assert_called_once()
        assert mock_search.call_args.kwargs["query"] == "do you have samsung phones?"

    def test_followup_without_existing_results_searches(self):
        state = {"messages": [HumanMessage(content="what colors?")]}

        with patch("src.Agent.nodes.retrieval.search_products_raw", return_value=[]) as mock_search:
            retrieval_node(state)

        mock_search.assert_called_once()


class TestIsFollowupQuestion:
    def test_english_followup(self):
        assert _is_followup_question("what colors does it come in?")

    def test_english_new_product(self):
        assert not _is_followup_question("show me asus laptop")

    def test_arabic_followup(self):
        assert _is_followup_question("لونه ايه؟")

    def test_arabic_new_product(self):
        assert not _is_followup_question("عايز لابتوب")


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
        # candidate pool is inflated (max(limit*3, 12)) so re-ranking has options
        assert call_kwargs[1]["limit"] == 12

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


class TestReRank:
    def test_empty(self):
        assert _rerank("laptop", []) == []

    def test_real_product_beats_accessory_for_laptop_query(self):
        products = [
            {"name": "Laptop Charger For ASUS Laptops - Black", "category": "Laptops & PCs",
             "thumbnail": "x", "stock_status": "IN_STOCK", "score": 0.9},
            {"name": "ASUS TUF A14 Gaming Laptop AMD Ryzen 9", "category": "Electronics",
             "thumbnail": "y", "stock_status": "IN_STOCK", "score": 0.75},
        ]
        ranked = _rerank("asus laptop", products)
        assert "Gaming Laptop" in ranked[0]["name"]
        assert "Charger" in ranked[1]["name"]

    def test_irrelevant_item_demoted_for_laptop_query(self):
        products = [
            {"name": "ASUS TUF A14 Gaming Laptop", "category": "Electronics",
             "thumbnail": "y", "stock_status": "IN_STOCK", "score": 0.7},
            {"name": "EA Sports FC 26 for PlayStation", "category": "Electronics",
             "thumbnail": "z", "stock_status": "IN_STOCK", "score": 0.85},
        ]
        ranked = _rerank("asus laptop", products)
        assert "Gaming Laptop" in ranked[0]["name"]
        assert "EA Sports" in ranked[1]["name"]

    def test_marketing_category_demoted(self):
        products = [
            {"name": "Foldable Laptop Stand", "category": "Laptops & PCs",
             "thumbnail": "a", "stock_status": "IN_STOCK", "score": 0.8},
            {"name": "Lenovo LOQ Gaming Laptop", "category": "Laptops",
             "thumbnail": "b", "stock_status": "IN_STOCK", "score": 0.7},
        ]
        ranked = _rerank("laptop", products)
        # marketing/accessory noise demoted below real laptop
        assert "Gaming Laptop" in ranked[0]["name"]

    def test_has_image_in_stock_prefer_for_best_match(self):
        products = [
            {"name": "HP OMEN Laptop", "category": "Laptops",
             "thumbnail": "", "stock_status": "OUT_OF_STOCK", "score": 0.8},
            {"name": "Dell XPS Laptop", "category": "Laptops",
             "thumbnail": "d", "stock_status": "IN_STOCK", "score": 0.6},
        ]
        ranked = _rerank("laptop", products)
        # Dell (has image + in stock) surfaces to front via best-first
        assert "Dell" in ranked[0]["name"]
