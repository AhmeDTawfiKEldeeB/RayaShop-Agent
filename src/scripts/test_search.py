from src.infrastructure.embeddings.factory import EmbeddingFactory
from src.infrastructure.vector_db.stores.weaviate_product_store import WeaviateProductStore


def main() -> None:
    store = WeaviateProductStore()
    embedder = EmbeddingFactory.create()

    queries = [
        "wireless headphones",
        "laptop bag",
        "gaming mouse",
        "phone case iphone",
        "usb cable",
    ]

    for query in queries:
        vector = embedder.embed_text(query)
        results = store.db.search(store.collection_name, query_vector=vector, limit=3)

        print(f'Search: "{query}"')
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r.score:.3f}] {r.payload['name']}  (id={r.payload['product_id']}, price={r.payload['price']})")
        print()

    store.close()


if __name__ == "__main__":
    main()
