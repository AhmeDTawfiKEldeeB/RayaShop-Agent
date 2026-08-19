import json

import httpx

from src.config.settings import settings
from ..base import BaseScraper
from ..models import ScrapedProduct


class RayaScraper(BaseScraper):
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

    def __init__(self):
        raya_settings = settings.scraper.raya

        self.base_url = raya_settings.base_url
        self.api_url = raya_settings.api_url
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

    async def scrape_products(self) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=30,
        ) as client:

            first_page = await self._fetch_page(
                client=client,
                page=1,
            )

            total_pages = first_page["page_info"]["total_pages"]
            total_count = first_page["total_count"]

            print(f"Total products: {total_count}")
            print(f"Total pages: {total_pages}")

            products.extend(
                self._parse_products(first_page["nodes"])
            )

            print(
                f"Page 1/{total_pages} "
                f"→ {len(first_page['nodes'])} products"
            )

            for page in range(2, total_pages + 1):

                connection = await self._fetch_page(
                    client=client,
                    page=page,
                )

                page_products = self._parse_products(
                    connection["nodes"]
                )

                products.extend(page_products)

                print(
                    f"Page {page}/{total_pages} "
                    f"→ {len(page_products)} products"
                )

        # Remove duplicates by product ID
        unique_products = {
            product.id: product
            for product in products
        }

        return list(unique_products.values())

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        page: int,
    ) -> dict:

        variables = {
            "page": page,
            "pageSize": self.page_size,
            "sort": {
                "position": "ASC",
            },
            "filter": {
                "seller_ids": [],
            },
            "withPaging": True,
        }

        response = await client.get(
            self.api_url,
            params={
                "query": self.QUERY,
                "variables": json.dumps(variables),
                "storeCode": self.store_code,
            },
        )

        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            raise RuntimeError(data["errors"])

        return data["data"]["connection"]

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

            thumbnail = product.get("thumbnail")

            images = [
                image["url"]
                for image in product.get("media_gallery", [])
                if not image.get("disabled", False)
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
                    stock_status=product.get("stock_status"),
                )
            )

        return result