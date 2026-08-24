from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.product import Product
from src.db.session import SessionLocal
from src.infrastructure.ingestion.product_ingestion import (
    ProductIngestion,
)
from src.infrastructure.scraping.providers.raya_product_details import (
    RayaProductDetails,
    RayaProductDetailsScraper,
)


# =============================================================
# PRODUCT TARGET
# =============================================================

@dataclass
class ProductTarget:
    id: int
    url: str


# =============================================================
# RAYA PRODUCT DETAILS INGESTION
# =============================================================

class RayaProductDetailsIngestion:

    # ---------------------------------------------------------
    # TEST LIMIT
    #
    # Start with 100 products.
    # After validating performance, change to:
    #
    #     TEST_LIMIT = None
    #
    # to process the complete catalog.
    # ---------------------------------------------------------

    TEST_LIMIT: int | None = None

    # ---------------------------------------------------------
    # Number of products that can be fetched concurrently.
    #
    # This should match the number of persistent Node workers.
    # ---------------------------------------------------------

    CONCURRENCY = 5

    # ---------------------------------------------------------
    # Number of products accumulated before DB ingestion.
    # ---------------------------------------------------------

    DB_BATCH_SIZE = 50

    # ---------------------------------------------------------
    # Retry configuration.
    # ---------------------------------------------------------

    MAX_RETRIES = 3

    RETRY_DELAY = 2.0

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

        # One persistent Node worker per concurrency slot.
        #
        # This is the important optimization:
        #
        # OLD:
        #     Product -> spawn Node -> resolve -> kill Node
        #
        # NEW:
        #     Start 5 Node workers once
        #     -> reuse them for all products
        #
        self.scraper = (
            RayaProductDetailsScraper(
                node_workers=self.CONCURRENCY
            )
        )

        self.ingestion = (
            ProductIngestion(
                session
            )
        )

        self.semaphore = asyncio.Semaphore(
            self.CONCURRENCY
        )

    # =========================================================
    # LOAD PRODUCTS
    # =========================================================

    def load_products(
        self,
        limit: int | None = None,
    ) -> list[ProductTarget]:

        statement = (
            select(
                Product.id,
                Product.url,
            )
            .where(
                Product.url.is_not(None)
            )
            .order_by(
                Product.id
            )
        )

        if limit is not None:

            statement = statement.limit(
                limit
            )

        rows = (
            self.session.execute(
                statement
            )
            .all()
        )

        return [
            ProductTarget(
                id=row.id,
                url=row.url,
            )
            for row in rows
        ]

    # =========================================================
    # SCRAPE ONE PRODUCT
    # =========================================================

    async def _scrape_one(
        self,
        product: ProductTarget,
    ) -> RayaProductDetails | None:

        async with self.semaphore:

            for attempt in range(
                1,
                self.MAX_RETRIES + 1,
            ):

                try:

                    print(
                        f"[FETCH] "
                        f"id={product.id} "
                        f"attempt={attempt}"
                    )

                    details = (
                        await self.scraper.scrape(
                            product_id=product.id,
                            url=product.url,
                        )
                    )

                    return details

                except Exception as exc:

                    print(
                        f"[ERROR] "
                        f"id={product.id} "
                        f"attempt={attempt} "
                        f"error={exc}"
                    )

                    if attempt < self.MAX_RETRIES:

                        delay = (
                            self.RETRY_DELAY
                            * attempt
                        )

                        print(
                            f"[RETRY] "
                            f"id={product.id} "
                            f"waiting={delay:.1f}s"
                        )

                        await asyncio.sleep(
                            delay
                        )

            return None

    # =========================================================
    # SCRAPE BATCH
    # =========================================================

    async def _scrape_batch(
        self,
        products: list[ProductTarget],
    ) -> tuple[
        list[RayaProductDetails],
        list[int],
    ]:

        tasks = [
            self._scrape_one(
                product
            )
            for product in products
        ]

        results = await asyncio.gather(
            *tasks
        )

        successful: list[
            RayaProductDetails
        ] = []

        failed: list[int] = []

        for product, details in zip(
            products,
            results,
        ):

            if details is None:

                failed.append(
                    product.id
                )

            else:

                successful.append(
                    details
                )

        return successful, failed

    # =========================================================
    # RUN
    # =========================================================

    async def run(
        self,
        limit: int | None = None,
    ) -> None:

        products = self.load_products(
            limit=limit
        )

        print()
        print("=" * 70)
        print(
            "RAYA PRODUCT DETAILS INGESTION"
        )
        print("=" * 70)

        print(
            f"Products loaded : "
            f"{len(products)}"
        )

        print(
            f"Concurrency      : "
            f"{self.CONCURRENCY}"
        )

        print(
            f"Node workers     : "
            f"{self.CONCURRENCY}"
        )

        print(
            f"DB batch size    : "
            f"{self.DB_BATCH_SIZE}"
        )

        print(
            f"Max retries      : "
            f"{self.MAX_RETRIES}"
        )

        print("=" * 70)

        if not products:

            print(
                "No products found."
            )

            return

        total = len(products)

        successful_count = 0

        failed_ids: list[int] = []

        # -----------------------------------------------------
        # Process products in DB batches.
        # -----------------------------------------------------

        for start in range(
            0,
            total,
            self.DB_BATCH_SIZE,
        ):

            batch = products[
                start:start
                + self.DB_BATCH_SIZE
            ]

            batch_end = min(
                start + len(batch),
                total,
            )

            print()
            print(
                "=" * 70
            )

            print(
                f"Batch "
                f"{start + 1}-"
                f"{batch_end}/"
                f"{total}"
            )

            print(
                "=" * 70
            )

            # -------------------------------------------------
            # Scrape batch concurrently.
            # -------------------------------------------------

            details, failed = (
                await self._scrape_batch(
                    batch
                )
            )

            # -------------------------------------------------
            # Add failed IDs to global list.
            # -------------------------------------------------

            failed_ids.extend(
                failed
            )

            # -------------------------------------------------
            # Save successful details.
            # -------------------------------------------------

            if details:

                try:

                    self.ingestion.ingest_details(
                        details
                    )

                    successful_count += (
                        len(details)
                    )

                except Exception:

                    self.session.rollback()

                    print(
                        "Database batch failed. "
                        "Transaction rolled back."
                    )

                    raise

            # -------------------------------------------------
            # Progress
            # -------------------------------------------------

            processed = (
                batch_end
            )

            print()
            print(
                f"Progress: "
                f"{processed}/{total}"
            )

            print(
                f"Successful: "
                f"{successful_count}"
            )

            print(
                f"Failed: "
                f"{len(failed_ids)}"
            )

    # =========================================================
    # FINAL REPORT
    # =========================================================

        print()
        print("=" * 70)
        print(
            "DETAIL INGESTION FINISHED"
        )
        print("=" * 70)

        print(
            f"Total products : "
            f"{total}"
        )

        print(
            f"Successful     : "
            f"{successful_count}"
        )

        print(
            f"Failed         : "
            f"{len(failed_ids)}"
        )

        if failed_ids:

            print()
            print(
                "FAILED PRODUCT IDS"
            )

            print("-" * 70)

            for product_id in failed_ids:

                print(
                    product_id
                )

            print("-" * 70)

        else:

            print(
                "All products processed "
                "successfully."
            )

        print("=" * 70)


# =============================================================
# MAIN
# =============================================================

async def main():

    session = SessionLocal()

    crawler = None

    try:

        crawler = (
            RayaProductDetailsIngestion(
                session
            )
        )

        await crawler.run(
            limit=(
                RayaProductDetailsIngestion.TEST_LIMIT
            )
        )

    except Exception:

        session.rollback()

        print()
        print(
            "Crawler failed. "
            "Database transaction rolled back."
        )

        raise

    finally:

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # Close all persistent Node workers.
        # Otherwise node.exe processes will remain alive.
        # -----------------------------------------------------

        if crawler is not None:

            try:

                crawler.scraper.close()

            except Exception as exc:

                print(
                    f"⚠ Failed to close "
                    f"Node worker pool: {exc}"
                )

        session.close()


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )