import asyncio
import json

import httpx

from src.config.settings import settings


# =========================================================
# CATEGORY QUERY
# =========================================================

CATEGORY_QUERY = """
query Products(
    $page: Int!
    $pageSize: Int!
    $filter: ProductAttributeFilterInput
) {
    connection: products(
        currentPage: $page
        pageSize: $pageSize
        filter: $filter
    ) {
        total_count

        nodes: items {
            id
            name
            sku
        }

        page_info {
            current_page
            total_pages
            page_size
        }
    }
}
"""


# =========================================================
# CATEGORY TREE QUERY
# =========================================================

CATEGORIES_QUERY = """
query Categories {
    categories {
        items {
            uid
            id
            name
            level

            children {
                uid
                id
                name
                level

                children {
                    uid
                    id
                    name
                    level
                }
            }
        }
    }
}
"""


# =========================================================
# MAIN CATALOG ROOTS
# =========================================================

MAIN_CATEGORIES = {
    "Coffee Corner",
    "Mobiles & Tablets",
    "Televisions",
    "Large Appliances",
    "Small Appliances",
    "Kitchen Appliances",
    "Laptops & PCs",
    "Health & Beauty",
    "Electronics",
    "Home",
}


# =========================================================
# HELPERS
# =========================================================

def collect_leaf_categories(category: dict) -> list[dict]:
    """
    Recursively collect leaf categories.
    """

    children = category.get("children") or []

    if not children:
        return [category]

    leaves = []

    for child in children:
        leaves.extend(
            collect_leaf_categories(child)
        )

    return leaves


async def fetch_connection(
    client: httpx.AsyncClient,
    raya,
    *,
    page: int,
    page_size: int,
    category_uid: str | None = None,
) -> dict:
    """
    Fetch one products page.
    """

    filter_data = {
        "seller_ids": [],
    }

    if category_uid:
        filter_data["category_uid"] = {
            "eq": category_uid,
        }

    variables = {
        "page": page,
        "pageSize": page_size,
        "filter": filter_data,
    }

    response = await client.get(
        raya.api_url,
        params={
            "query": CATEGORY_QUERY,
            "variables": json.dumps(variables),
            "storeCode": raya.store_code,
        },
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(
            json.dumps(
                data["errors"],
                indent=2,
                ensure_ascii=False,
            )
        )

    return data["data"]["connection"]


# =========================================================
# GET DEFAULT PRODUCTS
# =========================================================

async def crawl_default_products(
    client: httpx.AsyncClient,
    raya,
) -> dict[str, dict]:
    """
    Crawl the current default listing.
    This gives us the baseline to compare against
    the category crawl.
    """

    page_size = 100

    print("=" * 70)
    print("DEFAULT CATALOG")
    print("=" * 70)

    first_page = await fetch_connection(
        client,
        raya,
        page=1,
        page_size=page_size,
    )

    total_count = first_page["total_count"]
    total_pages = first_page["page_info"]["total_pages"]

    print(f"API total : {total_count}")
    print(f"Pages     : {total_pages}")
    print("=" * 70)

    products: dict[str, dict] = {}

    for product in first_page["nodes"]:
        products[str(product["id"])] = product

    print(
        f"Page 1/{total_pages} "
        f"→ {len(first_page['nodes'])} "
        f"| unique={len(products)}"
    )

    for page in range(2, total_pages + 1):

        connection = await fetch_connection(
            client,
            raya,
            page=page,
            page_size=page_size,
        )

        nodes = connection["nodes"]

        for product in nodes:
            products[str(product["id"])] = product

        print(
            f"Page {page}/{total_pages} "
            f"→ {len(nodes)} "
            f"| unique={len(products)}"
        )

    return products


# =========================================================
# GET CATEGORY TREE
# =========================================================

async def get_leaf_categories(
    client: httpx.AsyncClient,
    raya,
) -> list[dict]:
    """
    Get leaf categories from the real catalog branches only.
    """

    response = await client.get(
        raya.api_url,
        params={
            "query": CATEGORIES_QUERY,
            "storeCode": raya.store_code,
        },
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(
            json.dumps(
                data["errors"],
                indent=2,
                ensure_ascii=False,
            )
        )

    roots = data["data"]["categories"]["items"]

    if not roots:
        return []

    root = roots[0]

    main_categories = [
        category
        for category in root.get("children") or []
        if category["name"].strip() in MAIN_CATEGORIES
    ]

    leaves = []

    for category in main_categories:
        leaves.extend(
            collect_leaf_categories(category)
        )

    # Deduplicate by UID
    leaves = list({
        category["uid"]: category
        for category in leaves
    }.values())

    return leaves


# =========================================================
# CRAWL ALL LEAF CATEGORIES
# =========================================================

async def crawl_all_categories(
    client: httpx.AsyncClient,
    raya,
    leaves: list[dict],
) -> dict[str, dict]:
    """
    Crawl every leaf category and merge products
    into one global dictionary.
    """

    page_size = 100

    all_products: dict[str, dict] = {}

    print()
    print("=" * 70)
    print("CATEGORY COVERAGE CRAWL")
    print("=" * 70)

    print(
        f"Leaf categories: {len(leaves)}"
    )

    print("=" * 70)

    for index, category in enumerate(
        leaves,
        start=1,
    ):

        uid = category["uid"]
        name = category["name"]

        try:

            first_page = await fetch_connection(
                client,
                raya,
                page=1,
                page_size=page_size,
                category_uid=uid,
            )

            total_count = first_page["total_count"]
            total_pages = first_page["page_info"]["total_pages"]

            category_new = 0

            for product in first_page["nodes"]:

                product_id = str(product["id"])

                if product_id not in all_products:
                    all_products[product_id] = product
                    category_new += 1

            print(
                f"[{index:02d}/{len(leaves)}] "
                f"{name} | "
                f"{total_count} products | "
                f"{total_pages} pages | "
                f"new={category_new} | "
                f"global={len(all_products)}"
            )

            for page in range(
                2,
                total_pages + 1,
            ):

                connection = await fetch_connection(
                    client,
                    raya,
                    page=page,
                    page_size=page_size,
                    category_uid=uid,
                )

                nodes = connection["nodes"]

                page_new = 0

                for product in nodes:

                    product_id = str(product["id"])

                    if product_id not in all_products:
                        all_products[product_id] = product
                        page_new += 1

                print(
                    f"    page {page}/{total_pages} "
                    f"→ {len(nodes)} "
                    f"| new={page_new} "
                    f"| global={len(all_products)}"
                )

        except Exception as exc:

            print(
                f"[{index:02d}/{len(leaves)}] "
                f"{name} | ERROR: {exc}"
            )

    return all_products


# =========================================================
# MAIN
# =========================================================

async def main():

    raya = settings.scraper.raya

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Origin": raya.base_url,
        "Referer": f"{raya.base_url}/",
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=60,
    ) as client:

        # -----------------------------------------------------
        # 1. Baseline
        # -----------------------------------------------------

        default_products = await crawl_default_products(
            client,
            raya,
        )

        print()
        print(
            f"Default unique products: "
            f"{len(default_products)}"
        )

        # -----------------------------------------------------
        # 2. Discover real catalog leaves
        # -----------------------------------------------------

        leaves = await get_leaf_categories(
            client,
            raya,
        )

        print()
        print(
            f"Catalog leaf categories: "
            f"{len(leaves)}"
        )

        # -----------------------------------------------------
        # 3. Crawl all leaves
        # -----------------------------------------------------

        category_products = await crawl_all_categories(
            client,
            raya,
            leaves,
        )

        # -----------------------------------------------------
        # 4. Compare
        # -----------------------------------------------------

        default_ids = set(
            default_products.keys()
        )

        category_ids = set(
            category_products.keys()
        )

        new_ids = (
            category_ids
            - default_ids
        )

        missing_from_categories = (
            default_ids
            - category_ids
        )

        overlap = (
            default_ids
            & category_ids
        )

        print()
        print("=" * 70)
        print("COVERAGE RESULT")
        print("=" * 70)

        print(
            f"Default unique products       : "
            f"{len(default_ids)}"
        )

        print(
            f"Category unique products      : "
            f"{len(category_ids)}"
        )

        print(
            f"Overlap                        : "
            f"{len(overlap)}"
        )

        print(
            f"New products from categories  : "
            f"{len(new_ids)}"
        )

        print(
            f"Default products not in leaves: "
            f"{len(missing_from_categories)}"
        )

        print("=" * 70)

        if new_ids:

            print(
                "✅ Categories discovered products "
                "that the default crawl missed."
            )

        else:

            print(
                "❌ Categories did not add any "
                "new products."
            )

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())