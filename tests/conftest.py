def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a running vector database (Qdrant/Weaviate)",
    )
