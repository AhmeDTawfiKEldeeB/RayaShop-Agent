import json
import sys
import time

from src.config.settings import settings
from src.db.models.product import Product
from src.db.session import SessionLocal
from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.interface import Distance, VectorRecord
from src.infrastructure.vector_db.providers.qdrant import QdrantDB

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EMBED_BATCH = 128


def clean_garbled_text(text: str) -> str:
    """Replace garbled diameter and multiplication signs in scraped text."""
    if not text:
        return ""
    text = text.replace("أک", "Ø")
    text = text.replace("أ—", "x")
    return text


def build_embedding_text(product: Product) -> str:
    """Build the semantic text representation of a product for embedding."""
    parts: list[str] = []

    if product.name:
        parts.append(f"Product: {clean_garbled_text(product.name)}")

    if product.brand:
        parts.append(f"Brand: {clean_garbled_text(product.brand)}")

    if product.category:
        parts.append(f"Category: {clean_garbled_text(product.category)}")

    if product.description:
        parts.append(f"Description: {clean_garbled_text(product.description)}")

    if product.short_description:
        parts.append(f"Short Description: {clean_garbled_text(product.short_description)}")

    if product.attributes:
        for key, value in product.attributes.items():
            if value is None:
                continue
            key_text = clean_garbled_text(str(key).strip())
            value_text = clean_garbled_text(str(value).strip())
            if not key_text or not value_text:
                continue
            parts.append(f"{key_text}: {value_text}")

    return "\n".join(parts)


def main() -> None:
    # Initialize connection to Qdrant
    db = QdrantDB()
    embedder = EmbeddingFactory.create()
    
    collection_name = settings.qdrant.collection_name
    vector_size = settings.qdrant.vector_size  # Usually 384 for MiniLM-L12-v2
    distance_metric = settings.qdrant.distance_metric.lower()

    # Resolve distance metric
    distance = Distance.COSINE
    for d in Distance:
        if d.value == distance_metric:
            distance = d
            break

    # Count products in Postgres
    session = SessionLocal()
    try:
        total = session.query(Product).count()
        print(f"Found {total} products in Postgres", flush=True)
    finally:
        session.close()

    if total == 0:
        print("No products to ingest", flush=True)
        db.close()
        return

    # Reset collection in Qdrant
    print(f"Recreating Qdrant collection '{collection_name}' (size={vector_size}, distance={distance.value})...")
    if db.collection_exists(collection_name):
        db.delete_collection(collection_name)
    db.create_collection(collection_name, vector_size=vector_size, distance=distance)
    print("Collection created.")

    # Warm up embedding models
    print("Loading embedding models (dense and sparse)...")
    t_warm = time.monotonic()
    embedder.embed_text("warmup")
    from fastembed import SparseTextEmbedding
    sparse_embedder = SparseTextEmbedding(model_name="Qdrant/bm25")
    # Warm up sparse model by embedding a small token
    list(sparse_embedder.embed(["warmup"]))
    print(f"Models ready in {time.monotonic() - t_warm:.1f}s")

    # Ingest loop
    session = SessionLocal()
    ingested = 0
    global_start = time.monotonic()

    try:
        for offset in range(0, total, EMBED_BATCH):
            batch = (
                session.query(Product)
                .order_by(Product.id)
                .offset(offset)
                .limit(min(EMBED_BATCH, total - offset))
                .all()
            )

            # Build embedding texts
            texts = [build_embedding_text(p) for p in batch]

            # Generate vectors (dense and sparse)
            t0 = time.monotonic()
            vectors = embedder.embed_documents(texts)
            sparse_vectors = list(sparse_embedder.embed(texts))
            embed_time = time.monotonic() - t0

            # Build Qdrant records
            records = []
            for product, vector, sparse_vector in zip(batch, vectors, sparse_vectors):
                attributes = {
                    clean_garbled_text(str(k)): clean_garbled_text(str(v))
                    for k, v in (product.attributes or {}).items()
                    if v is not None
                }

                payload = {
                    "product_id": product.id,
                    "name": clean_garbled_text(product.name or ""),
                    "sku": product.sku or "",
                    "brand": clean_garbled_text(product.brand or ""),
                    "category": clean_garbled_text(product.category or ""),
                    "description": clean_garbled_text(product.description or ""),
                    "short_description": clean_garbled_text(product.short_description or ""),
                    "attributes": json.dumps(attributes, ensure_ascii=False),
                    "price": float(product.price) if product.price is not None else 0.0,
                    "old_price": float(product.old_price) if product.old_price is not None else 0.0,
                    "stock_status": product.stock_status or "",
                    "url": product.url or "",
                    "thumbnail": product.thumbnail or "",
                }

                records.append(
                    VectorRecord(
                        id=int(product.id),
                        vector={
                            "": vector,
                            "sparse": sparse_vector,
                        },
                        payload=payload,
                    )
                )

            # Upload to Qdrant
            t1 = time.monotonic()
            db.upsert(collection_name, records)
            upsert_time = time.monotonic() - t1

            # Progress reporting
            ingested += len(batch)
            elapsed = time.monotonic() - global_start
            rate = ingested / elapsed if elapsed > 0 else 0
            print(f"[{ingested}/{total}] embed={embed_time:.1f}s upsert={upsert_time:.1f}s rate={rate:.0f}/s", flush=True)

    except Exception as exc:
        session.rollback()
        print(f"Ingestion failed: {exc}", flush=True)
        raise
    finally:
        session.close()

    elapsed = time.monotonic() - global_start
    print(f"\nDone: {ingested} products embedded and uploaded to Qdrant in {elapsed:.1f}s", flush=True)
    db.close()


if __name__ == "__main__":
    main()
