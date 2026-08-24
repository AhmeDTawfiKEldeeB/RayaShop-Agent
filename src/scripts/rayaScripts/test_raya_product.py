import asyncio

from src.infrastructure.scraping.providers.raya import RayaScraper


async def main():
    scraper = RayaScraper()

    products = await scraper.scrape_products()

    matches = [
        product
        for product in products
        if "OPPO A6 Pro" in product.name
        or "A6 Pro" in product.name
        or "A6 Pro" in product.sku
    ]

    print("\n" + "=" * 60)
    print("SEARCH RESULT")
    print("=" * 60)

    print(f"Total scraped: {len(products)}")
    print(f"Matches: {len(matches)}")

    for product in matches:
        print("\nFOUND:")
        print(f"ID: {product.id}")
        print(f"Name: {product.name}")
        print(f"SKU: {product.sku}")
        print(f"URL: {product.url}")
        print(f"Price: {product.price}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())