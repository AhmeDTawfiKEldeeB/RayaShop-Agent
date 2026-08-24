import asyncio

from src.infrastructure.scraping.providers.raya import RayaScraper


async def main():
    scraper = RayaScraper()
    products = await scraper.scrape_products()

    print(f"\nFinal products: {len(products)}")


if __name__ == "__main__":
    asyncio.run(main())