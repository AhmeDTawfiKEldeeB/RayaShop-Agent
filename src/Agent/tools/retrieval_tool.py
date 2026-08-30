import json
import logging
import re
from typing import Any

from langchain_core.tools import tool

from src.config.settings import settings
from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.factory import VectorDBFactory
from src.infrastructure.vector_db.interface import VectorStore

logger = logging.getLogger(__name__)

_embedder = None
_db = None

# A local dictionary mapping common Arabic brand names to their English equivalents.
# This helps guide the multilingual embedding model during cross-lingual searches
# where the product database contains English brands but users search in Arabic script.
BRAND_MAPPING = {
    "فريش": "Fresh",
    "توشيبا": "Toshiba",
    "سامسونج": "Samsung",
    "كيريازي": "Kiriazi",
    "كريازي": "Kiriazi",
    "كريازى": "Kiriazi",
    "زانوسي": "Zanussi",
    "زانوسى": "Zanussi",
    "بيكو": "Beko",
    "ال جي": "LG",
    "إل جي": "LG",
    "تورنيدو": "Tornado",
    "تورنادو": "Tornado",
    "يونيون اير": "Unionaire",
    "يونيون إير": "Unionaire",
    "شارب": "Sharp",
    "ميديا": "Midea",
    "اريستون": "Ariston",
    "أريستون": "Ariston",
    "وايت بوينت": "White Point",
    "بوش": "Bosch",
    "سوناي": "Sonai",
    "جاك": "JAC",
    "وايت ويل": "White Whale",
}


def contains_arabic(text: str) -> bool:
    """Check if the string contains Arabic characters."""
    # Arabic Unicode block range: U+0600 to U+06FF
    return bool(re.search(r"[\u0600-\u06ff]", text))


def _get_embedder() -> Any:
    """Get or initialize the embedding provider.
    
    Used for warming up the model during startup.
    """
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingFactory.create()
    return _embedder


def _get_db() -> VectorStore:
    """Get or initialize the database client dynamically."""
    global _db
    if _db is None:
        provider = settings.vector_db_provider
        logger.info("Initializing vector database provider: %s", provider)
        _db = VectorDBFactory.create(provider)
    return _db


def close_db() -> None:
    """Close the database connection if initialized."""
    global _db
    if _db is not None:
        try:
            _db.close()
        except Exception:
            pass
        _db = None


@tool
def retrieve_products(query: str, limit: int = 5) -> str:
    """Retrieve products matching the query from the active Vector Database.

    Args:
        query: The search query (e.g. "refrigerator", "water dispenser", "iPhone").
        limit: The maximum number of products to return (default is 5).

    Returns:
        A JSON string containing list of retrieved products with their details.
    """
    try:
        embedder = _get_embedder()
        db = _get_db()

        # Step 1: Expand query with English brand equivalents if Arabic brand names are found.
        # This gives a strong cross-lingual cue to the E5-small multilingual model.
        expanded_query = query
        for arabic_brand, english_brand in BRAND_MAPPING.items():
            if arabic_brand in query:
                if english_brand.lower() not in query.lower():
                    expanded_query += f" {english_brand}"
                    logger.info("Expanded brand in query: '%s' -> '%s'", query, expanded_query)

        # Step 2: E5 models require a "query: " prefix for search queries
        model_name = settings.embedding.huggingface.model_name.lower()
        if settings.embedding.provider == "huggingface" and "e5" in model_name:
            embedding_query = f"query: {expanded_query}"
        else:
            embedding_query = expanded_query

        logger.info("Generating embedding for formatted query: '%s'", embedding_query)
        query_vector = embedder.embed_text(embedding_query)

        # Step 3: Determine alpha based on query language.
        # Since the database contains only English text, an Arabic text query will 
        # return 0 real BM25 matches. However, garbled characters (e.g. 'أک' scraped 
        # from diameter symbols 'Ø') can trigger false positive BM25 matches, which 
        # ruins the result set.
        # Setting alpha = 1.0 (pure vector search) for Arabic queries completely 
        # avoids this noise and uses the multilingual embedding model's cross-lingual capabilities.
        if contains_arabic(query):
            alpha = 1.0
            logger.info("Arabic query detected. Using pure vector search (alpha=1.0) to prevent BM25 noise.")
        else:
            alpha = 0.5
            logger.info("English query detected. Using balanced hybrid search (alpha=0.5).")

        # Step 4: Resolve collection name and query properties based on provider
        provider = settings.vector_db_provider.lower()
        if provider == "qdrant":
            collection_name = settings.qdrant.collection_name
        else:
            collection_name = settings.weaviate.product_collection_name

        logger.info(
            "Performing search on collection: %s (%s) with limit: %d and alpha: %.2f",
            collection_name,
            provider,
            limit,
            alpha,
        )

        results = db.hybrid_search(
            collection_name=collection_name,
            query_text=expanded_query,
            query_vector=query_vector,
            limit=limit,
            alpha=alpha,
        )

        retrieved_items = []
        for r in results:
            # Ignore low-relevance vector noise if score is below threshold
            if r.score < 0.15:
                continue
            # Reconstruct the item details including the database ID and search score
            item = {
                "id": r.id,
                "score": r.score,
                "name": r.payload.get("name", ""),
                "sku": r.payload.get("sku", ""),
                "brand": r.payload.get("brand", ""),
                "category": r.payload.get("category", ""),
                "price": r.payload.get("price", 0.0),
                "old_price": r.payload.get("old_price", 0.0),
                "stock_status": r.payload.get("stock_status", ""),
                "url": r.payload.get("url", ""),
                "thumbnail": r.payload.get("thumbnail", ""),
            }
            # Attempt to parse serialised attributes if present
            attrs = r.payload.get("attributes")
            if attrs and isinstance(attrs, str):
                try:
                    item["attributes"] = json.loads(attrs)
                except json.JSONDecodeError:
                    item["attributes"] = attrs
            retrieved_items.append(item)

        return json.dumps(retrieved_items, ensure_ascii=False, indent=2)

    except Exception as exc:
        logger.exception("Error during product retrieval")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def search_products_raw(query: str, limit: int = 7) -> list[dict]:
    """Search products and return raw dict results (for API use, not as a tool)."""
    result_str = retrieve_products.invoke({"query": query, "limit": limit})
    return json.loads(result_str)
