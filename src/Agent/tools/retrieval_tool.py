import json
import logging

from langchain_core.tools import tool

from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.stores.weaviate_product_store import (
    WeaviateProductStore,
)

logger = logging.getLogger(__name__)

_store: WeaviateProductStore | None = None
_embedder = None

_MIN_VECTOR_SCORE = 0.45


def _get_store() -> WeaviateProductStore:
    global _store
    if _store is None:
        _store = WeaviateProductStore()
    return _store


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingFactory.create()
    return _embedder


def search_products_raw(query: str, limit: int = 7) -> list[dict]:
    store = _get_store()
    embedder = _get_embedder()

    vector = embedder.embed_text(query)

    probe = store.db.search(store.collection_name, query_vector=vector, limit=1)
    top_score = probe[0].score if probe else 0.0
    if top_score < _MIN_VECTOR_SCORE:
        logger.info("search_products: query %r below threshold %.3f -> empty", query, top_score)
        return []

    results = store.db.hybrid_search(
        store.collection_name,
        query_text=query,
        query_vector=vector,
        limit=limit,
    )

    products = []
    for r in results:
        products.append({
            "id": r.payload.get("product_id"),
            "name": r.payload.get("name", ""),
            "sku": r.payload.get("sku", ""),
            "price": r.payload.get("price", 0),
            "old_price": r.payload.get("old_price", 0),
            "stock_status": r.payload.get("stock_status", ""),
            "url": r.payload.get("url", ""),
            "thumbnail": r.payload.get("thumbnail", ""),
            "score": round(r.score, 4),
        })

    logger.info("search_products: query=%r returned %d results", query, len(products))
    return products


@tool
def search_products(query: str, limit: int = 7) -> str:
    """Search RayaShop product catalog using hybrid search (keyword + semantic).

    Use this tool when the user asks to find, search, or look up products.
    The query should describe what the user is looking for in natural language.

    Args:
        query: Natural language description of products to find.
               Examples: "wireless bluetooth headphones under 500 EGP",
                         "laptop bag 15 inch waterproof",
                         "gaming mouse rgb".
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        JSON string containing a list of matching products with name, price,
        old_price, stock_status, sku, url, and relevance score.
    """
    return json.dumps(search_products_raw(query, limit), ensure_ascii=False)
