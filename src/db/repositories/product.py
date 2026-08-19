from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models.product import Product
from src.db.models.product_image import ProductImage


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def get_by_sku(self, sku: str) -> Product | None:
        statement = select(Product).where(Product.sku == sku)
        return self.session.execute(statement).scalar_one_or_none()

    def upsert(self, product_data: dict) -> Product:
        statement = insert(Product).values(**product_data)
        update_values = {key: value for key, value in product_data.items() if key != "id"}
        statement = statement.on_conflict_do_update(index_elements=[Product.id], set_=update_values)
        self.session.execute(statement)
        product = self.session.get(Product, product_data["id"])
        if product is None:
            raise RuntimeError(f"Failed to upsert product {product_data['id']}")
        return product

    def delete_images(self, product_id: int) -> None:
        self.session.query(ProductImage).filter(ProductImage.product_id == product_id).delete(
            synchronize_session=False
        )

    def add_image(self, product_id: int, url: str, position: int) -> ProductImage:
        image = ProductImage(product_id=product_id, url=url, position=position)
        self.session.add(image)
        return image

    def save(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()