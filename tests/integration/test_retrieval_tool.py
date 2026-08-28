import json
import pytest
import sys

# Ensure UTF-8 output on Windows to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.Agent.tools.retrieval_tool import retrieve_products, close_db


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    close_db()



def test_retrieval_tool_returns_products():
    # Define a query that we know matches products in our database
    query = "   ميكسر للمطبخ  "
    limit = 3
    
    print(f"\n--- Testing retrieval tool with query: '{query}' ---")
    
    # Invoke the LangChain tool
    # A LangChain tool can be called directly or via tool.invoke()
    result_str = retrieve_products.invoke({"query": query, "limit": limit})
    
    # Assertions
    assert isinstance(result_str, str), "The tool must return a JSON string"
    
    # Parse the JSON string
    results = json.loads(result_str)
    assert isinstance(results, list), "Parsed results must be a list"
    
    print(f"Retrieved {len(results)} products:")
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
        
    assert len(results) > 0, "No products were retrieved from Weaviate"
    for item in results:
        assert "name" in item, "Item should have 'name'"
        assert "price" in item, "Item should have 'price'"


if __name__ == "__main__":
    try:
        test_retrieval_tool_returns_products()
    finally:
        close_db()


