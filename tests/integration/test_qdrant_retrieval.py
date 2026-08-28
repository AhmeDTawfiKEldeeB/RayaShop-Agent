import json
import pytest
import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.config.settings import settings

# Dynamically force Qdrant provider for this integration test
settings.vector_db_provider = "qdrant"

from src.Agent.tools.retrieval_tool import retrieve_products, close_db

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def cleanup_db():
    # Make sure we close connections after tests
    yield
    close_db()


def test_qdrant_retrieval_returns_products():
    query ="i need cover for iphone"
    limit = 10
    
    print(f"\n--- Testing Qdrant retrieval with query: '{query}' ---")
    
    # Invoke the retrieval tool (which now dynamically uses Qdrant)
    result_str = retrieve_products.invoke({"query": query, "limit": limit})
    
    # Assertions
    assert isinstance(result_str, str), "The tool must return a JSON string"
    
    # Parse the JSON string
    results = json.loads(result_str)
    
    if "error" in results:
        pytest.fail(f"Tool returned an error: {results['error']}")
        
    assert isinstance(results, list), "Parsed results must be a list"
    
    print(f"Retrieved {len(results)} products from Qdrant:")
    for idx, item in enumerate(results, 1):
        print(f"\nProduct #{idx}:")
        print(f"  ID: {item.get('id')}")
        print(f"  Name: {item.get('name')}")
        print(f"  Brand: {item.get('brand')}")
        print(f"  Price: EGP {item.get('price')}")
        print(f"  SKU: {item.get('sku')}")
        print(f"  Category: {item.get('category')}")
        print(f"  Stock Status: {item.get('stock_status')}")
        print(f"  URL: {item.get('url')}")
        print(f"  Score: {item.get('score')}")
        
    assert len(results) > 0, "No products were retrieved from Qdrant"
    for item in results:
        assert "name" in item, "Item should have 'name'"
        assert "price" in item, "Item should have 'price'"


if __name__ == "__main__":
    test_qdrant_retrieval_returns_products()
