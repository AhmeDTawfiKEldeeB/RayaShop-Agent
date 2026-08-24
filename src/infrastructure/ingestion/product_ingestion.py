from decimal import Decimal

from sqlalchemy.orm import Session

from src.db.models.product import Product
from src.db.models.product_image import ProductImage
from src.infrastructure.scraping.factory import ScraperFactory
from src.infrastructure.scraping.models import ScrapedProduct
from src.infrastructure.scraping.providers.raya_product_details import (
    RayaProductDetails,
)


class ProductIngestion:

    BATCH_SIZE = 500

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

    # =========================================================
    # BASIC PRODUCT INGESTION
    # =========================================================

    def ingest(
        self,
        products: list[ScrapedProduct],
    ) -> None:

        if not products:
            print("No products to ingest")
            return

        total = len(products)

        print(
            f"Ingesting {total} products..."
        )

        for start in range(
            0,
            total,
            self.BATCH_SIZE,
        ):
            batch = products[
                start:start + self.BATCH_SIZE
            ]

            product_rows: list[dict] = []
            image_rows: list[dict] = []
            product_ids: list[int] = []

            # -------------------------------------------------
            # BUILD PRODUCT ROWS
            # -------------------------------------------------

            for product in batch:

                product_ids.append(
                    product.id
                )

                product_rows.append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "sku": product.sku,
                        "url": product.url,
                        "price": (
                            Decimal(
                                str(
                                    product.price
                                )
                            )
                            if product.price is not None
                            else None
                        ),
                        "old_price": (
                            Decimal(
                                str(
                                    product.old_price
                                )
                            )
                            if product.old_price is not None
                            else None
                        ),
                        "thumbnail": product.thumbnail,
                        "stock_status": product.stock_status,
                    }
                )

                # -------------------------------------------------
                # BUILD IMAGE ROWS
                # -------------------------------------------------

                for position, image_url in enumerate(
                    product.images
                ):
                    image_rows.append(
                        {
                            "product_id": product.id,
                            "url": image_url,
                            "position": position,
                        }
                    )

            # -------------------------------------------------
            # UPSERT BASIC PRODUCTS
            # -------------------------------------------------

            self._bulk_upsert_products(
                product_rows
            )

            # -------------------------------------------------
            # REPLACE IMAGES
            # -------------------------------------------------

            self._replace_images(
                product_ids=product_ids,
                image_rows=image_rows,
            )

            current = min(
                start + len(batch),
                total,
            )

            print(
                f"Processed "
                f"{current}/{total} products"
            )

        self.session.commit()

        print(
            "Basic product ingestion "
            "completed successfully"
        )

    # =========================================================
    # BULK UPSERT BASIC PRODUCTS
    # =========================================================

    def _bulk_upsert_products(
        self,
        rows: list[dict],
    ) -> None:

        if not rows:
            return

        from sqlalchemy.dialects.postgresql import insert

        statement = (
            insert(Product)
            .values(rows)
        )

        # Do not overwrite rich detail fields during
        # the basic catalog ingestion.
        update_values = {
            column.name: getattr(
                statement.excluded,
                column.name,
            )
            for column in Product.__table__.columns
            if column.name != "id"
            and column.name != "created_at"
            and column.name not in {
                "brand",
                "category",
                "description",
                "short_description",
                "attributes",
            }
        }

        statement = (
            statement.on_conflict_do_update(
                index_elements=[
                    Product.id
                ],
                set_=update_values,
            )
        )

        self.session.execute(
            statement
        )

    # =========================================================
    # REPLACE PRODUCT IMAGES
    # =========================================================

    def _replace_images(
        self,
        product_ids: list[int],
        image_rows: list[dict],
    ) -> None:

        if not product_ids:
            return

        # -----------------------------------------------------
        # Delete all existing images for this batch.
        #
        # This also handles the case where a product currently
        # has no images.
        # -----------------------------------------------------

        self.session.execute(
            ProductImage.__table__.delete().where(
                ProductImage.product_id.in_(
                    product_ids
                )
            )
        )

        # -----------------------------------------------------
        # Insert current images
        # -----------------------------------------------------

        if not image_rows:
            return

        from sqlalchemy.dialects.postgresql import insert

        for start in range(
            0,
            len(image_rows),
            self.BATCH_SIZE,
        ):
            batch = image_rows[
                start:start + self.BATCH_SIZE
            ]

            self.session.execute(
                insert(
                    ProductImage
                ).values(batch)
            )

    # =========================================================
    # PRODUCT DETAILS INGESTION
    # =========================================================

    def ingest_details(
        self,
        details_list: list[RayaProductDetails],
    ) -> None:

        if not details_list:
            print(
                "No product details to ingest"
            )
            return

        total = len(
            details_list
        )

        print(
            f"Ingesting details for "
            f"{total} products..."
        )

        for start in range(
            0,
            total,
            self.BATCH_SIZE,
        ):
            batch = details_list[
                start:start + self.BATCH_SIZE
            ]

            self._update_product_details_batch(
                batch
            )

            current = min(
                start + len(batch),
                total,
            )

            print(
                f"Details processed "
                f"{current}/{total}"
            )

        self.session.commit()

        print(
            "Product details ingestion "
            "completed successfully"
        )

    # =========================================================
    # UPDATE EXISTING PRODUCTS WITH RICH DETAILS
    # =========================================================

    def _update_product_details_batch(
        self,
        details_list: list[RayaProductDetails],
    ) -> None:

        if not details_list:
            return

        product_ids = [
            details.product_id
            for details in details_list
        ]

        # -----------------------------------------------------
        # Load existing products.
        #
        # This is intentionally an UPDATE flow, not an INSERT
        # flow. The basic catalog ingestion already created
        # these products in PostgreSQL.
        # -----------------------------------------------------

        existing_products = (
            self.session.query(Product)
            .filter(
                Product.id.in_(product_ids)
            )
            .all()
        )

        products_by_id = {
            product.id: product
            for product in existing_products
        }

        for details in details_list:

            product = products_by_id.get(
                details.product_id
            )

            if product is None:

                print(
                    f"⚠ Product "
                    f"{details.product_id} "
                    f"not found in PostgreSQL"
                )

                continue

            # -------------------------------------------------
            # Only update rich fields.
            #
            # We intentionally leave:
            # name
            # sku
            # url
            # price
            # old_price
            # thumbnail
            # stock_status
            #
            # untouched here.
            # -------------------------------------------------

            if details.brand:

                product.brand = (
                    details.brand
                )

            if details.category:

                product.category = (
                    details.category
                )

            if details.description:

                product.description = (
                    details.description
                )

            if details.short_description:

                product.short_description = (
                    details.short_description
                )

            if details.attributes:

                product.attributes = (
                    details.attributes
                )

    # =========================================================
    # UPDATE ONE PRODUCT DETAILS
    # =========================================================

    def update_details(
        self,
        details: RayaProductDetails,
    ) -> None:

        product = self.session.get(
            Product,
            details.product_id,
        )

        if product is None:

            raise ValueError(
                f"Product {details.product_id} "
                "does not exist in PostgreSQL"
            )

        # -----------------------------------------------------
        # Only update fields that actually exist in the
        # scraped detail page.
        # -----------------------------------------------------

        if details.brand:

            product.brand = (
                details.brand
            )

        if details.category:

            product.category = (
                details.category
            )

        if details.description:

            product.description = (
                details.description
            )

        if details.short_description:

            product.short_description = (
                details.short_description
            )

        if details.attributes:

            product.attributes = (
                details.attributes
            )

    # =========================================================
    # RUN BASIC CATALOG PIPELINE
    # =========================================================

    @staticmethod
    async def run() -> None:

        from src.db.session import SessionLocal

        scraper = ScraperFactory.create(
            "raya"
        )

        print(
            "Starting Raya scraper..."
        )

        products = (
            await scraper.scrape_products()
        )

        print(
            f"Scraped {len(products)} products"
        )

        session = SessionLocal()

        try:

            ingestion = ProductIngestion(
                session
            )

            ingestion.ingest(
                products
            )

        except Exception:

            session.rollback()

            print(
                "Database ingestion failed. "
                "Transaction rolled back."
            )

            raise

        finally:

            session.close()