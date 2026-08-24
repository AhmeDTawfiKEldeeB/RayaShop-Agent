import asyncio
import json

from src.infrastructure.scraping.providers.raya_product_details import (
    RayaProductDetailsScraper,
)


async def main():

    scraper = RayaProductDetailsScraper()

    product_id = 281127

    url = (
        "https://www.rayashop.com/en/"
        "oppo-a6-pro-dual-sim-5g"
    )

    details = await scraper.scrape(
        product_id=product_id,
        url=url,
    )

    print()
    print("=" * 70)
    print("PRODUCT DETAILS")
    print("=" * 70)

    print(
        json.dumps(
            {
                "product_id": details.product_id,
                "name": details.name,
                "sku": details.sku,
                "brand": details.brand,
                "category": details.category,
                "short_description": (
                    details.short_description
                ),
                "description": details.description,
                "specifications": (
                    details.specifications
                ),
                "attributes": (
                    details.attributes
                ),
                "price": details.price,
                "currency": details.currency,
                "stock_status": details.stock_status,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())