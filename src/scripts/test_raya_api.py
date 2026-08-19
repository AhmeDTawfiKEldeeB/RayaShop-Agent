import json

import httpx

API_URL = "https://api-rayashop.global.ssl.fastly.net/graphql"


QUERY = """
query Products(
    $page: Int,
    $pageSize: Int,
    $filter: ProductAttributeFilterInput = {},
    $sort: ProductAttributeSortInput = {},
    $withAggregations: Boolean = false,
    $withPaging: Boolean = false
) {
    connection: products(
        currentPage: $page
        pageSize: $pageSize
        filter: $filter
        sort: $sort
    ) {
        total_count

        aggregations @include(if: $withAggregations) {
            attribute_code
            label
            count
            position
            options {
                label
                count
                value
            }
        }

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


def fetch_page(
    client: httpx.Client,
    page: int,
    page_size: int = 20,
) -> dict:

    variables = {
        "page": page,
        "pageSize": page_size,
        "sort": {
            "position": "ASC"
        },
        "filter": {
            "category_uid": {
                "eq": "Mjcw"
            },
            "seller_ids": []
        },
        "withAggregations": False,
        "withPaging": True,
    }

    response = client.get(
        API_URL,
        params={
            "query": QUERY,
            "variables": json.dumps(variables),
            "storeCode": "en",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]["connection"]


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.rayashop.com/",
        "Origin": "https://www.rayashop.com",
        "Authorization": "Bearer b6ed07fd0afcf762272622ae493b4e4c",
    }

    all_products = []

    with httpx.Client(headers=headers) as client:

        # Fetch first page
        first_page = fetch_page(
            client=client,
            page=1,
        )

        total_count = first_page["total_count"]
        page_info = first_page["page_info"]

        total_pages = page_info["total_pages"]
        page_size = page_info["page_size"]

        print(f"Total products: {total_count}")
        print(f"Total pages: {total_pages}")
        print(f"Page size: {page_size}")
        print()

        # Add first page
        first_products = first_page["nodes"]

        all_products.extend(first_products)

        print(
            f"Page 1/{total_pages} "
            f"→ {len(first_products)} products"
        )

        # Fetch remaining pages
        for page in range(2, total_pages + 1):

            connection = fetch_page(
                client=client,
                page=page,
                page_size=page_size,
            )

            products = connection["nodes"]

            all_products.extend(products)

            print(
                f"Page {page}/{total_pages} "
                f"→ {len(products)} products"
            )

    print()
    print(f"Collected products: {len(all_products)}")

    # Remove duplicates using product ID
    unique_products = {
        product["id"]: product
        for product in all_products
    }

    print(f"Unique products: {len(unique_products)}")


if __name__ == "__main__":
    main()