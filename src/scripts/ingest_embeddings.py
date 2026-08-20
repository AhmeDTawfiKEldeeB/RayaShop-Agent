import time

from src.db.models.product import Product
from src.db.session import SessionLocal
from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.interface import VectorRecord
from src.infrastructure.vector_db.stores.weaviate_product_store import (
    WeaviateProductStore,
)

EMBED_BATCH = 256
UPSERT_BATCH = 128


def build_embedding_text(product: Product) -> str:
    parts = [product.name]
    if product.sku:
        parts.append(product.sku)
    if product.stock_status:
        parts.append(product.stock_status)
    return " | ".join(parts)


def main() -> None:
    store = WeaviateProductStore()
    embedder = EmbeddingFactory.create()

    session = SessionLocal()
    try:
        total = session.query(Product).count()
        print(f"Found {total} products in Postgres")
    finally:
        session.close()

    if total == 0:
        print("No products to ingest")
        return

    store.ping()
    store.ensure_collection()

    embedder_start = time.monotonic()
    print("Loading embedding model...")
    embedder.embed_text("warmup")
    print(f"Model ready in {time.monotonic() - embedder_start:.1f}s")

    session = SessionLocal()
    ingested = 0
    global_start = time.monotonic()

    try:
        for offset in range(0, total, EMBED_BATCH):
            batch = (
                session.query(Product)
                .offset(offset)
                .limit(EMBED_BATCH)
                .all()
            )
            if not batch:
                break

            texts = [build_embedding_text(p) for p in batch]
            t0 = time.monotonic()
            vectors = embedder.embed_documents(texts)
            embed_time = time.monotonic() - t0

            records = []
            for product, vector in zip(batch, vectors):
                records.append(
                    VectorRecord(
                        id=str(product.id),
                        vector=vector,
                        payload={
                            "product_id": product.id,
                            "name": product.name or "",
                            "sku": product.sku or "",
                            "price": float(product.price) if product.price is not None else 0.0,
                            "old_price": float(product.old_price) if product.old_price is not None else 0.0,
                            "stock_status": product.stock_status or "",
                            "url": product.url or "",
                            "thumbnail": product.thumbnail or "",
                        },
                    )
                )

            t1 = time.monotonic()
            store.db.upsert(store.collection_name, records)
            upsert_time = time.monotonic() - t1

            ingested += len(batch)
            elapsed = time.monotonic() - global_start
            rate = ingested / elapsed if elapsed > 0 else 0
            print(
                f"[{ingested}/{total}] "
                f"embed={embed_time:.1f}s  upsert={upsert_time:.1f}s  "
                f"rate={rate:.0f}/s"
            )

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    elapsed = time.monotonic() - global_start
    print(f"\nDone: {ingested} products embedded and uploaded in {elapsed:.1f}s")

    weaviate_count = store.db.count(store.collection_name)
    print(f"Weaviate collection count: {weaviate_count}")

    store.close()


if __name__ == "__main__":
    main()
