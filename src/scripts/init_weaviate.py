from src.infrastructure.vector_db.stores.weaviate_product_store import (
    WeaviateProductStore,
)


def main() -> None:
    store = WeaviateProductStore()
    try:
        if not store.ping():
            print("Weaviate connection failed - aborting initialization")
            return

        print("Connected to Weaviate (ping OK)")
        print(f"Product collection: {store.collection_name}")

        if store.ensure_collection():
            print("Collection created successfully")
        else:
            print("Collection already exists")

    finally:
        store.close()
        print("Weaviate client closed safely")


if __name__ == "__main__":
    main()