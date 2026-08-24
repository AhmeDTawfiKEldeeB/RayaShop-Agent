import asyncio

from src.db.session import SessionLocal
from src.infrastructure.ingestion.product_ingestion import (
    ProductIngestion,
)
from src.infrastructure.scraping.providers.raya_product_details import (
    RayaProductDetailsScraper,
)


async def main():

    product_id = 281127

    product_url = (
        "https://www.rayashop.com/en/"
        "oppo-a6-pro-dual-sim-5g"
    )

    print("=" * 70)
    print("RAYA PRODUCT DETAIL INGESTION TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Scrape details from Raya
    # ---------------------------------------------------------

    scraper = RayaProductDetailsScraper()

    print(
        f"Scraping product details: "
        f"{product_id}"
    )

    details = await scraper.scrape(
        product_id=product_id,
        url=product_url,
    )

    print()
    print(
        f"Name     : {details.name}"
    )

    print(
        f"Brand    : {details.brand}"
    )

    print(
        f"Category : {details.category}"
    )

    print(
        f"Description length: "
        f"{len(details.description)}"
    )

    print(
        f"Attributes count: "
        f"{len(details.attributes)}"
    )

    # ---------------------------------------------------------
    # 2. Save details into PostgreSQL
    # ---------------------------------------------------------

    session = SessionLocal()

    try:

        ingestion = ProductIngestion(
            session
        )

        ingestion.update_details(
            details
        )

        session.commit()

        print()
        print(
            "✓ Product details saved to PostgreSQL"
        )

    except Exception:

        session.rollback()

        print(
            "✗ Failed to save product details"
        )

        raise

    finally:

        session.close()

    print()
    print("=" * 70)
    print("TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())