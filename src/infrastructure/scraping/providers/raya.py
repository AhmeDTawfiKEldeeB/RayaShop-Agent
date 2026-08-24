import json

import httpx

from src.config.settings import settings
from ..base import BaseScraper
from ..models import ScrapedProduct


class RayaScraper(BaseScraper):

    # =========================================================
    # PRODUCTS QUERY
    # =========================================================

    QUERY = """
    query Products(
        $page: Int,
        $pageSize: Int,
        $filter: ProductAttributeFilterInput = {},
        $sort: ProductAttributeSortInput = {},
        $withPaging: Boolean = false
    ) {
        connection: products(
            currentPage: $page
            pageSize: $pageSize
            filter: $filter
            sort: $sort
        ) {
            total_count

            nodes: items {
                __typename
                id
                name
                sku
                url_key
                stock_status

                thumbnail {
                    url
                    label
                }

                price_range {
                    maximum_price {
                        final_price {
                            value
                        }

                        regular_price {
                            value
                        }
                    }
                }

                media_gallery {
                    label
                    url
                    position
                    disabled
                }
            }

            page_info @include(if: $withPaging) {
                total_pages
                current_page
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
    # REAL PRODUCT TAXONOMY
    # =========================================================

    MAIN_CATALOG_CATEGORIES = {
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
    # CATALOG SETTINGS
    # =========================================================

    CATALOG_PAGE_SIZE = 100

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):
        raya_settings = settings.scraper.raya

        self.base_url = raya_settings.base_url
        self.api_url = raya_settings.api_url
        self.api_key = raya_settings.api_key
        self.store_code = raya_settings.store_code
        self.page_size = raya_settings.page_size

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

        if self.api_key:
            self.headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

    # =========================================================
    # FULL CATALOG
    # =========================================================

    async def scrape_products(self) -> list[ScrapedProduct]:
        """
        Scrape the complete Raya catalog.

        Strategy:
            1. Crawl the default catalog.
            2. Discover the real product taxonomy.
            3. Crawl all leaf categories.
            4. Compare both sources.
            5. Merge and deduplicate by product ID.
            6. Print validation report.
        """

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=60,
        ) as client:

            print("=" * 70)
            print("RAYA FULL CATALOG SCRAPE")
            print("=" * 70)

            # =================================================
            # 1. DEFAULT CATALOG
            # =================================================

            default_products = await self._crawl_default_catalog(
                client=client
            )

            default_by_id = {
                product.id: product
                for product in default_products
            }

            print()
            print(
                f"Default catalog unique products: "
                f"{len(default_by_id)}"
            )

            # =================================================
            # 2. DISCOVER LEAF CATEGORIES
            # =================================================

            leaf_categories = await self._get_leaf_categories(
                client=client
            )

            print()
            print(
                f"Catalog leaf categories: "
                f"{len(leaf_categories)}"
            )

            # =================================================
            # 3. CATEGORY CRAWL
            # =================================================

            category_products_by_id: dict[
                int,
                ScrapedProduct,
            ] = {}

            failed_categories: list[str] = []

            print()
            print("=" * 70)
            print("CATEGORY CRAWL")
            print("=" * 70)

            print(
                f"Leaf categories: "
                f"{len(leaf_categories)}"
            )

            print("=" * 70)

            for index, category in enumerate(
                leaf_categories,
                start=1,
            ):

                category_name = category["name"]
                category_uid = category["uid"]

                try:

                    new_count = await self._crawl_one_category(
                        client=client,
                        category_name=category_name,
                        category_uid=category_uid,
                        products_by_id=category_products_by_id,
                    )

                    print(
                        f"[{index:02d}/{len(leaf_categories)}] "
                        f"{category_name} "
                        f"| new={new_count} "
                        f"| global={len(category_products_by_id)}"
                    )

                except Exception as exc:

                    failed_categories.append(
                        f"{category_name} "
                        f"(uid={category_uid})"
                    )

                    print(
                        f"[{index:02d}/{len(leaf_categories)}] "
                        f"{category_name} "
                        f"| ERROR: {exc}"
                    )

            # =================================================
            # 4. BUILD SETS
            # =================================================

            category_ids = set(
                category_products_by_id.keys()
            )

            default_ids = set(
                default_by_id.keys()
            )

            overlap_ids = (
                default_ids & category_ids
            )

            category_only_ids = (
                category_ids - default_ids
            )

            default_only_ids = (
                default_ids - category_ids
            )

            # =================================================
            # 5. MERGE
            # =================================================

            merged_products = {
                **default_by_id,
                **category_products_by_id,
            }

            # =================================================
            # 6. VALIDATION REPORT
            # =================================================

            print()
            print("=" * 70)
            print("RAYA SCRAPER VALIDATION")
            print("=" * 70)

            print(
                f"Default catalog products : "
                f"{len(default_ids)}"
            )

            print(
                f"Category products        : "
                f"{len(category_ids)}"
            )

            print(
                f"Overlap                  : "
                f"{len(overlap_ids)}"
            )

            print(
                f"New from categories      : "
                f"{len(category_only_ids)}"
            )

            print(
                f"Default-only products    : "
                f"{len(default_only_ids)}"
            )

            print(
                f"Final unique products    : "
                f"{len(merged_products)}"
            )

            print(
                f"Failed categories       : "
                f"{len(failed_categories)}"
            )

            print("=" * 70)

            # =================================================
            # 7. FAILED CATEGORIES
            # =================================================

            if failed_categories:

                print()
                print("FAILED CATEGORIES")
                print("-" * 70)

                for category in failed_categories:
                    print(category)

                print("-" * 70)

            else:

                print(
                    "All catalog categories scraped successfully."
                )

            print("=" * 70)

            return list(
                merged_products.values()
            )

    # =========================================================
    # DEFAULT CATALOG CRAWL
    # =========================================================

    async def _crawl_default_catalog(
        self,
        client: httpx.AsyncClient,
    ) -> list[ScrapedProduct]:

        products_by_id: dict[
            int,
            ScrapedProduct,
        ] = {}

        first_page = await self._fetch_product_page(
            client=client,
            page=1,
            page_size=self.CATALOG_PAGE_SIZE,
            filter_data={
                "seller_ids": [],
            },
        )

        total_count = first_page["total_count"]

        total_pages = (
            first_page["page_info"]["total_pages"]
        )

        print()
        print("=" * 70)
        print("DEFAULT CATALOG")
        print("=" * 70)

        print(
            f"API total products : "
            f"{total_count}"
        )

        print(
            f"API total pages    : "
            f"{total_pages}"
        )

        print(
            f"Page size          : "
            f"{self.CATALOG_PAGE_SIZE}"
        )

        print("=" * 70)

        new_count = self._add_products(
            products_by_id=products_by_id,
            products=first_page["nodes"],
        )

        print(
            f"Page 1/{total_pages} → "
            f"{len(first_page['nodes'])} products "
            f"| new={new_count} "
            f"| unique={len(products_by_id)}"
        )

        for page in range(
            2,
            total_pages + 1,
        ):

            connection = await self._fetch_product_page(
                client=client,
                page=page,
                page_size=self.CATALOG_PAGE_SIZE,
                filter_data={
                    "seller_ids": [],
                },
            )

            nodes = connection["nodes"]

            new_count = self._add_products(
                products_by_id=products_by_id,
                products=nodes,
            )

            print(
                f"Page {page}/{total_pages} → "
                f"{len(nodes)} products "
                f"| new={new_count} "
                f"| unique={len(products_by_id)}"
            )

        return list(
            products_by_id.values()
        )

    # =========================================================
    # CATEGORY DISCOVERY
    # =========================================================

    async def _get_leaf_categories(
        self,
        client: httpx.AsyncClient,
    ) -> list[dict]:

        response = await client.get(
            self.api_url,
            params={
                "query": self.CATEGORIES_QUERY,
                "storeCode": self.store_code,
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

        roots = (
            data
            .get("data", {})
            .get("categories", {})
            .get("items", [])
        )

        if not roots:
            raise RuntimeError(
                "Raya categories API returned no root categories."
            )

        root = roots[0]

        level_2_categories = (
            root.get("children") or []
        )

        # Only keep the real catalog branches.
        catalog_roots = [
            category
            for category in level_2_categories
            if category["name"].strip()
            in self.MAIN_CATALOG_CATEGORIES
        ]

        if not catalog_roots:
            raise RuntimeError(
                "No main catalog categories were discovered."
            )

        leaf_categories: list[dict] = []

        for category in catalog_roots:

            leaf_categories.extend(
                self._collect_leaf_categories(
                    category
                )
            )

        # Deduplicate by category UID.
        unique_categories = {
            category["uid"]: category
            for category in leaf_categories
        }

        return list(
            unique_categories.values()
        )

    def _collect_leaf_categories(
        self,
        category: dict,
    ) -> list[dict]:

        children = (
            category.get("children")
            or []
        )

        if not children:
            return [category]

        leaves: list[dict] = []

        for child in children:

            leaves.extend(
                self._collect_leaf_categories(
                    child
                )
            )

        return leaves

    # =========================================================
    # CRAWL ONE CATEGORY
    # =========================================================

    async def _crawl_one_category(
        self,
        client: httpx.AsyncClient,
        category_name: str,
        category_uid: str,
        products_by_id: dict[
            int,
            ScrapedProduct,
        ],
    ) -> int:

        first_page = await self._fetch_product_page(
            client=client,
            page=1,
            page_size=self.CATALOG_PAGE_SIZE,
            filter_data={
                "category_uid": {
                    "eq": category_uid,
                }
            },
        )

        total_count = first_page["total_count"]

        total_pages = (
            first_page["page_info"]["total_pages"]
        )

        category_new = self._add_products(
            products_by_id=products_by_id,
            products=first_page["nodes"],
        )

        print(
            f"[CATEGORY] {category_name} "
            f"| {total_count} products "
            f"| {total_pages} pages"
        )

        for page in range(
            2,
            total_pages + 1,
        ):

            connection = await self._fetch_product_page(
                client=client,
                page=page,
                page_size=self.CATALOG_PAGE_SIZE,
                filter_data={
                    "category_uid": {
                        "eq": category_uid,
                    }
                },
            )

            nodes = connection["nodes"]

            category_new += self._add_products(
                products_by_id=products_by_id,
                products=nodes,
            )

        return category_new

    # =========================================================
    # PRODUCT SEARCH
    # =========================================================

    async def search_products(
        self,
        query: str,
    ) -> list[ScrapedProduct]:

        query = query.strip()

        if not query:
            return []

        products_by_id: dict[
            int,
            ScrapedProduct,
        ] = {}

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=60,
        ) as client:

            first_page = await self._fetch_search_page(
                client=client,
                page=1,
                query=query,
            )

            total_pages = (
                first_page["page_info"]["total_pages"]
            )

            total_count = (
                first_page["total_count"]
            )

            print("=" * 60)
            print("RAYA PRODUCT SEARCH")
            print("=" * 60)

            print(
                f"Search query       : "
                f"{query}"
            )

            print(
                f"API total results  : "
                f"{total_count}"
            )

            print(
                f"Total pages        : "
                f"{total_pages}"
            )

            print("=" * 60)

            new_count = self._add_products(
                products_by_id=products_by_id,
                products=first_page["nodes"],
            )

            print(
                f"Page 1/{total_pages} → "
                f"{len(first_page['nodes'])} products "
                f"| new={new_count} "
                f"| unique={len(products_by_id)}"
            )

            for page in range(
                2,
                total_pages + 1,
            ):

                connection = await self._fetch_search_page(
                    client=client,
                    page=page,
                    query=query,
                )

                nodes = connection["nodes"]

                new_count = self._add_products(
                    products_by_id=products_by_id,
                    products=nodes,
                )

                print(
                    f"Page {page}/{total_pages} → "
                    f"{len(nodes)} products "
                    f"| new={new_count} "
                    f"| unique={len(products_by_id)}"
                )

        print("=" * 60)
        print("SEARCH FINISHED")
        print("=" * 60)

        print(
            f"Unique products : "
            f"{len(products_by_id)}"
        )

        return list(
            products_by_id.values()
        )

    # =========================================================
    # FETCH PRODUCT PAGE
    # =========================================================

    async def _fetch_product_page(
        self,
        client: httpx.AsyncClient,
        page: int,
        page_size: int,
        filter_data: dict,
    ) -> dict:

        variables = {
            "page": page,
            "pageSize": page_size,
            "sort": {
                "position": "ASC",
            },
            "filter": filter_data,
            "withPaging": True,
        }

        response = await client.get(
            self.api_url,
            params={
                "query": self.QUERY,
                "variables": json.dumps(
                    variables
                ),
                "storeCode": self.store_code,
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

        connection = (
            data
            .get("data", {})
            .get("connection")
        )

        if connection is None:
            raise RuntimeError(
                "Missing products connection "
                f"for page={page}, "
                f"filter={filter_data}"
            )

        return connection

    # =========================================================
    # FETCH SEARCH PAGE
    # =========================================================

    async def _fetch_search_page(
        self,
        client: httpx.AsyncClient,
        page: int,
        query: str,
    ) -> dict:

        variables = {
            "page": page,
            "pageSize": self.page_size,
            "sort": {
                "position": "ASC",
            },
            "filter": {
                "name": {
                    "match": query,
                },
                "seller_ids": [],
            },
            "withPaging": True,
        }

        response = await client.get(
            self.api_url,
            params={
                "query": self.QUERY,
                "variables": json.dumps(
                    variables
                ),
                "storeCode": self.store_code,
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

        connection = (
            data
            .get("data", {})
            .get("connection")
        )

        if connection is None:
            raise RuntimeError(
                "Missing search connection "
                f"for query={query}, "
                f"page={page}"
            )

        return connection

    # =========================================================
    # ADD + DEDUP PRODUCTS
    # =========================================================

    def _add_products(
        self,
        products_by_id: dict[
            int,
            ScrapedProduct,
        ],
        products: list[dict],
    ) -> int:

        parsed_products = self._parse_products(
            products
        )

        new_count = 0

        for product in parsed_products:

            if product.id not in products_by_id:
                new_count += 1

            products_by_id[product.id] = product

        return new_count

    # =========================================================
    # PARSE PRODUCTS
    # =========================================================

    def _parse_products(
        self,
        products: list[dict],
    ) -> list[ScrapedProduct]:

        result: list[ScrapedProduct] = []

        for product in products:

            maximum_price = (
                product["price_range"]["maximum_price"]
            )

            final_price = (
                maximum_price["final_price"]["value"]
            )

            regular_price = (
                maximum_price["regular_price"]["value"]
            )

            thumbnail = product.get(
                "thumbnail"
            )

            images = [
                image["url"]
                for image in product.get(
                    "media_gallery",
                    [],
                )
                if not image.get(
                    "disabled",
                    False,
                )
            ]

            result.append(
                ScrapedProduct(
                    id=product["id"],
                    name=product["name"],
                    sku=product["sku"],
                    url=(
                        f"{self.base_url}/en/"
                        f"{product['url_key']}"
                    ),
                    price=final_price,
                    old_price=(
                        regular_price
                        if regular_price != final_price
                        else None
                    ),
                    thumbnail=(
                        thumbnail["url"]
                        if thumbnail
                        else None
                    ),
                    images=images,
                    stock_status=product.get(
                        "stock_status"
                    ),
                )
            )

        return result


# =============================================================
# OPTIONAL DIRECT TEST
# =============================================================

async def main():

    scraper = RayaScraper()

    products = await scraper.scrape_products()

    print()
    print("=" * 70)
    print("FINAL PRODUCTS")
    print("=" * 70)

    print(
        f"Final products: {len(products)}"
    )

    print("=" * 70)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())