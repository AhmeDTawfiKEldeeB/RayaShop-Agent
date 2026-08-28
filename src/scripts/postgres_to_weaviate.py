import time
import json
from src.db.models.product import Product
from src.db.session import SessionLocal
from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.interface import VectorRecord
from src.infrastructure.vector_db.stores.weaviate_product_store import (
    WeaviateProductStore,
)


EMBED_BATCH = 128


def clean_garbled_text(text: str) -> str:
    """Replace garbled diameter and multiplication signs in scraped text."""
    if not text:
        return ""
    text = text.replace("أک", "Ø")
    text = text.replace("أ—", "x")
    return text


def build_embedding_text(
    product: Product,
) -> str:
    """
    Build the semantic representation of a product.

    The embedding should contain information that helps
    understand what the product IS and what it contains.

    Dynamic / filterable values such as price and stock are
    intentionally kept out of the embedding.
    """

    parts: list[str] = []

    # ---------------------------------------------------------
    # Product name
    # ---------------------------------------------------------

    if product.name:
        parts.append(
            f"Product: {clean_garbled_text(product.name)}"
        )

    # ---------------------------------------------------------
    # Brand
    # ---------------------------------------------------------

    if product.brand:
        parts.append(
            f"Brand: {clean_garbled_text(product.brand)}"
        )

    # ---------------------------------------------------------
    # Category
    # ---------------------------------------------------------

    if product.category:
        parts.append(
            f"Category: {clean_garbled_text(product.category)}"
        )

    # ---------------------------------------------------------
    # Description
    # ---------------------------------------------------------

    if product.description:
        parts.append(
            f"Description: {clean_garbled_text(product.description)}"
        )

    # ---------------------------------------------------------
    # Short description
    # ---------------------------------------------------------

    if product.short_description:
        parts.append(
            f"Short Description: "
            f"{clean_garbled_text(product.short_description)}"
        )

    # ---------------------------------------------------------
    # Product attributes
    # ---------------------------------------------------------

    if product.attributes:

        for key, value in product.attributes.items():

            if value is None:
                continue

            key_text = clean_garbled_text(str(key).strip())
            value_text = clean_garbled_text(str(value).strip())

            if not key_text or not value_text:
                continue

            parts.append(
                f"{key_text}: {value_text}"
            )

    return "\n".join(parts)



def main() -> None:

    # =========================================================
    # INITIALIZE
    # =========================================================

    store = WeaviateProductStore()

    embedder = EmbeddingFactory.create()

    # =========================================================
    # COUNT PRODUCTS
    # =========================================================

    session = SessionLocal()

    try:

        total = (
            session.query(Product)
            .count()
        )

        print(
            f"Found {total} products in Postgres",
            flush=True,
        )

    finally:

        session.close()

    if total == 0:

        print(
            "No products to ingest",
            flush=True,
        )

        store.close()

        return

    # =========================================================
    # WEAVIATE — drop and recreate collection
    # =========================================================

    store.ping()

    name = store.collection_name
    old_count = store.db.count(name)
    print(f"Deleting old collection '{name}' ({old_count} objects)...")
    store.db.delete_collection(name)
    print("Deleted")

    print(f"Creating new collection '{name}'...")
    store.create_collection()
    print("Created")

    # =========================================================
    # LOAD EMBEDDING MODEL
    # =========================================================

    embedder_start = time.monotonic()

    print(
        "Loading embedding model..."
    )

    embedder.embed_text(
        "warmup"
    )

    print(
        "Model ready in "
        f"{time.monotonic() - embedder_start:.1f}s"
    )

    # =========================================================
    # INGEST
    # =========================================================

    session = SessionLocal()

    ingested = 0

    global_start = time.monotonic()

    try:

        for offset in range(
            0,
            total,
            EMBED_BATCH,
        ):

            # -------------------------------------------------
            # Load products
            # -------------------------------------------------
            batch = (
                session.query(Product)
                .order_by(Product.id)
                .offset(offset)
                .limit(
                    min(
                        EMBED_BATCH,
                        total - offset,
                    )
                )
                .all()
)

            # -------------------------------------------------
            # Build rich embedding texts
            # -------------------------------------------------

            texts = [
                build_embedding_text(
                    product
                )
                for product in batch
            ]

            # -------------------------------------------------
            # Embeddings
            # -------------------------------------------------

            t0 = time.monotonic()

            vectors = (
                embedder.embed_documents(
                    texts
                )
            )

            embed_time = (
                time.monotonic() - t0
            )

            # -------------------------------------------------
            # Build Weaviate records
            # -------------------------------------------------

            records: list[
                VectorRecord
            ] = []

            for product, vector in zip(
                batch,
                vectors,
            ):

                attributes = {
                    clean_garbled_text(str(k)): clean_garbled_text(str(v))
                    for k, v in (product.attributes or {}).items()
                    if v is not None
                }

                records.append(
                    VectorRecord(
                        id=str(
                            product.id
                        ),
                        vector=vector,
                        payload={
                            # ---------------------------------
                            # Identification
                            # ---------------------------------

                            "product_id": (
                                product.id
                            ),

                            "name": (
                                clean_garbled_text(product.name or "")
                            ),

                            "sku": (
                                product.sku
                                or ""
                            ),

                            # ---------------------------------
                            # Rich product information
                            # ---------------------------------

                            "brand": (
                                clean_garbled_text(product.brand or "")
                            ),

                            "category": (
                                clean_garbled_text(product.category or "")
                            ),

                            "description": (
                                clean_garbled_text(product.description or "")
                            ),

                            "short_description": (
                                clean_garbled_text(product.short_description or "")
                            ),

                            "attributes": json.dumps(
                                attributes,
                                ensure_ascii=False,
                            ),


                            # ---------------------------------
                            # Pricing
                            # ---------------------------------

                            "price": (
                                float(product.price)
                                if product.price
                                is not None
                                else 0.0
                            ),

                            "old_price": (
                                float(
                                    product.old_price
                                )
                                if product.old_price
                                is not None
                                else 0.0
                            ),

                            # ---------------------------------
                            # Availability
                            # ---------------------------------

                            "stock_status": (
                                product.stock_status
                                or ""
                            ),

                            # ---------------------------------
                            # Product link / image
                            # ---------------------------------

                            "url": (
                                product.url
                                or ""
                            ),

                            "thumbnail": (
                                product.thumbnail
                                or ""
                            ),
                        },
                    )
                )

            # -------------------------------------------------
            # Weaviate upsert
            # -------------------------------------------------

            t1 = time.monotonic()

            # UPSERT_BATCH is kept as a configurable value.
            #
            # If your store.db.upsert already handles batching
            # internally, this single call is enough.
            store.db.upsert(
                store.collection_name,
                records,
            )

            upsert_time = (
                time.monotonic() - t1
            )

            # -------------------------------------------------
            # Progress
            # -------------------------------------------------

            ingested += len(
                batch
            )

            elapsed = (
                time.monotonic()
                - global_start
            )

            rate = (
                ingested / elapsed
                if elapsed > 0
                else 0
            )

            print(
                f"[{ingested}/{total}] "
                f"embed={embed_time:.1f}s "
                f"upsert={upsert_time:.1f}s "
                f"rate={rate:.0f}/s"
            )

    except Exception:

        session.rollback()

        raise

    finally:

        session.close()

    # =========================================================
    # FINAL REPORT
    # =========================================================

    elapsed = (
        time.monotonic()
        - global_start
    )

    print(
        "\nDone: "
        f"{ingested} products embedded "
        f"and uploaded in "
        f"{elapsed:.1f}s"
    )

    weaviate_count = (
        store.db.count(
            store.collection_name
        )
    )

    print(
        "Weaviate collection count: "
        f"{weaviate_count}"
    )

    store.close()


if __name__ == "__main__":
    main()