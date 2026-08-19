import asyncio

from src.infrastructure.scraping.factory import ScraperFactory


async def main():
    scraper = ScraperFactory.create("raya")

    products = await scraper.scrape_products()

    print(f"Found {len(products)} products")

    for product in products[:5]:
        print()
        print(f"Name: {product.name}")
        print(f"SKU: {product.sku}")
        print(f"Price: {product.price}")
        print(f"Old Price: {product.old_price}")
        print(f"URL: {product.url}")
        print(f"Thumbnail: {product.thumbnail}")
        print(f"Images: {len(product.images)}")
        print(f"Stock: {product.stock_status}")


if __name__ == "__main__":
    asyncio.run(main())