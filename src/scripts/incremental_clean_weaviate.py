import json
import logging
import re
import sys
import time
from typing import ClassVar

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from src.db.models.product import Product
from src.db.session import SessionLocal
from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.interface import VectorRecord
from src.infrastructure.vector_db.stores.weaviate_product_store import WeaviateProductStore


def clean_garbled_text(text: str) -> str:
    """Replace garbled diameter and multiplication signs in scraped text."""
    if not text:
        return ""
    text = text.replace("أک", "Ø")
    text = text.replace("أ—", "x")
    return text


def build_embedding_text(product: Product) -> str:
    """Build the clean semantic text representation of the product for embedding."""
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


def contains_garbled(text: str) -> bool:
    """Check if the text contains any of the known garbled sequences."""
    if not text:
        return False
    return "أک" in text or "أ—" in text


def is_affected(product: Product) -> bool:
    """Determine if a product contains any garbled characters in its fields."""
    if contains_garbled(product.name):
        return True
    if contains_garbled(product.brand):
        return True
    if contains_garbled(product.category):
        return True
    if contains_garbled(product.description):
        return True
    if contains_garbled(product.short_description):
        return True
    if product.attributes:
        for k, v in product.attributes.items():
            if contains_garbled(str(k)) or contains_garbled(str(v)):
                return True
    return False


def main() -> None:
    logger.info("Initializing migration client connections...")
    store = WeaviateProductStore()
    embedder = EmbeddingFactory.create()
    session = SessionLocal()

    try:
        # Step 1: Scan Postgres for affected products
        logger.info("Scanning Postgres for products containing garbled characters...")
        all_products = session.query(Product).all()
        logger.info("Total products loaded from Postgres: %d", len(all_products))

        affected_products = [p for p in all_products if is_affected(p)]
        logger.info("Found %d products affected by garbled characters.", len(affected_products))

        if not affected_products:
            logger.info("No affected products found. Database is already clean.")
            return

        # Step 2: Warm up embedding model
        logger.info("Warming up embedding model...")
        embedder.embed_text("warmup")

        # Step 3: Incremental updates in batches
        batch_size = 128
        total_updated = 0
        logger.info("Starting incremental re-embedding and updating Weaviate...")

        for start in range(0, len(affected_products), batch_size):
            batch = affected_products[start : start + batch_size]
            
            # Build cleaned embedding texts
            texts = [build_embedding_text(p) for p in batch]
            
            # Generate new vector embeddings
            vectors = embedder.embed_documents(texts)

            # Build Weaviate records with cleaned payload
            records = []
            for product, vector in zip(batch, vectors):
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
                        id=str(product.id),
                        vector=vector,
                        payload=payload,
                    )
                )

            # Upsert into Weaviate
            store.db.upsert(store.collection_name, records)
            total_updated += len(records)
            logger.info("Progress: Updated %d / %d products", total_updated, len(affected_products))

        logger.info("Migration completed successfully! Cleaned and re-embedded %d products.", total_updated)

    except Exception as exc:
        logger.exception("Migration failed")
    finally:
        session.close()
        store.close()
        logger.info("Clean connections closed safely.")


if __name__ == "__main__":
    main()
