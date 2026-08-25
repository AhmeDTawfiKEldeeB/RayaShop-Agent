"""Golden evaluation set for the retrieval tool.

Each case defines:
  - query: the search text
  - expect_any: list of lowercase keywords; a result is "relevant" if its
    product name contains at least one keyword. Empty list = expect NO results.
  - note: why this case exists
"""

GOLDEN_SET: list[dict] = [
    {
        "query": "SONY WH-1000XM5",
        "expect_any": ["wh-1000xm5"],
        "note": "Exact model number — keyword/BM25 should dominate",
    },
    {
        "query": "iphone 15",
        "expect_any": ["iphone 15"],
        "note": "Brand + model",
    },
    {
        "query": "wireless headphones",
        "expect_any": ["wireless", "headphone"],
        "note": "Generic category — semantic should dominate",
    },
    {
        "query": "gaming mouse",
        "expect_any": ["gaming mouse", "gaming"],
        "note": "Category + use case",
    },
    {
        "query": "laptop bag",
        "expect_any": ["laptop"],
        "note": "Accessory category",
    },
    {
        "query": "airpods pro",
        "expect_any": ["airpods"],
        "note": "Apple accessory by common name",
    },
    {
        "query": "55 inch tv",
        "expect_any": ["55"],
        "note": "Size attribute in name",
    },
    {
        "query": "power bank",
        "expect_any": ["power bank", "powerbank"],
        "note": "Two-word accessory",
    },
    {
        "query": "اهلا",
        "expect_any": [],
        "note": "Arabic greeting — must return nothing",
    },
    {
        "query": "hello",
        "expect_any": [],
        "note": "English greeting — must return nothing",
    },
    {
        "query": "flying car with wings",
        "expect_any": [],
        "note": "Non-catalog nonsense — must return nothing",
    },
    {
        "query": "xyzabc 999 fake product",
        "expect_any": [],
        "note": "Garbage tokens — must return nothing",
    },
]
