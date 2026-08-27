import json
import logging

from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.stores.weaviate_product_store import (
    WeaviateProductStore,
)

logger = logging.getLogger(__name__)

_store: WeaviateProductStore | None = None
_embedder = None


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


def search_products_raw(
    query: str,
    limit: int = 7,
) -> list[dict]:
    """
    Search RayaShop products using hybrid search.

    The retrieval layer is responsible for:
    - query embedding
    - hybrid search
    - extracting product metadata

    It does not perform greeting detection or off-topic detection.
    Those responsibilities belong to the Agent guardrails layer.
    """
    query = query.strip()
    if not query:
        return []
    store = _get_store()
    embedder = _get_embedder()

    vector = embedder.embed_text(query)

    results = store.db.hybrid_search(
        store.collection_name,
        query_text=query,
        query_vector=vector,
        limit=limit,
    )

    products: list[dict] = []

    for result in results:
        payload = result.payload or {}

        products.append(
            {

                "id": payload.get("product_id"),
                "name": payload.get("name","",),
                "sku": payload.get("sku","",),
                "brand": payload.get("brand","",),
                "category": payload.get("category","",),
                "description": payload.get("description","",),
                "short_description": payload.get("short_description","",),
                "attributes": payload.get("attributes",{},),
                "price": payload.get("price",0,),
                "old_price": payload.get("old_price",0,),
                "stock_status": payload.get("stock_status","",),
                "url": payload.get("url","",),
                "thumbnail": payload.get("thumbnail","",),
                "score": round(result.score,4,),
            }
        )

    logger.info(
        "search_products: query=%r returned %d results",
        query,
        len(products),
    )

    return products

def format_search_results(
    products: list[dict],
) -> str:
    """
    Serialize retrieval results for Agent state/context.

    Keeps the JSON representation stable and readable.
    """

    return json.dumps(
        products,
        ensure_ascii=False,
    )