from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models.product import Product
from src.db.models.product_image import ProductImage
from src.infrastructure.scraping.factory import ScraperFactory
from src.infrastructure.scraping.models import ScrapedProduct


class ProductIngestion:
    BATCH_SIZE = 500

    def __init__(self, session: Session):
        self.session = session

    def ingest(self, products: list[ScrapedProduct]) -> None:
        if not products:
            print("No products to ingest")
            return

        print(f"Ingesting {len(products)} products...")

        for start in range(0, len(products), self.BATCH_SIZE):
            batch = products[start:start + self.BATCH_SIZE]

            product_rows = []
            image_rows = []

            for p in batch:
                product_rows.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "sku": p.sku,
                        "url": p.url,
                        "price": Decimal(str(p.price)) if p.price is not None else None,
                        "old_price": (
                            Decimal(str(p.old_price))
                            if p.old_price is not None
                            else None
                        ),
                        "thumbnail": p.thumbnail,
                        "stock_status": p.stock_status,
                    }
                )

                for position, image_url in enumerate(p.images):
                    image_rows.append(
                        {
                            "product_id": p.id,
                            "url": image_url,
                            "position": position,
                        }
                    )

            self._bulk_upsert_products(product_rows)
            self._replace_images(image_rows)

            current = min(start + len(batch), len(products))
            print(f"Processed {current}/{len(products)} products")

        self.session.commit()
        print("Database ingestion completed successfully")

    def _bulk_upsert_products(self, rows: list[dict]) -> None:
        if not rows:
            return

        stmt = insert(Product).values(rows)

        update_cols = {
            column.name: getattr(stmt.excluded, column.name)
            for column in Product.__table__.columns
            if column.name != "id"
            and column.name not in {"created_at"}
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=[Product.id],
            set_=update_cols,
        )

        self.session.execute(stmt)

    def _replace_images(self, rows: list[dict]) -> None:
        if not rows:
            return

        product_ids = {row["product_id"] for row in rows}

        self.session.execute(
            ProductImage.__table__.delete().where(
                ProductImage.product_id.in_(product_ids)
            )
        )

        for start in range(0, len(rows), self.BATCH_SIZE):
            batch = rows[start:start + self.BATCH_SIZE]
            self.session.execute(
                insert(ProductImage).values(batch)
            )

    @staticmethod
    async def run() -> None:
        from src.db.session import SessionLocal

        scraper = ScraperFactory.create("raya")

        print("Starting Raya scraper...")
        products = await scraper.scrape_products()

        print(f"Scraped {len(products)} products")

        session = SessionLocal()

        try:
            ingestion = ProductIngestion(session)
            ingestion.ingest(products)

        except Exception:
            session.rollback()
            print("Database ingestion failed. Transaction rolled back.")
            raise

        finally:
            session.close()