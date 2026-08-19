"""create products and product_images tables

Revision ID: 23ce02c69b3f
Revises:
Create Date: 2026-08-18 16:52:39.703436
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "23ce02c69b3f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sku", sa.String(255), unique=True, nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("stock_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_products_sku", "products", ["sku"])
    op.create_index("idx_products_name_trgm", "products", ["name"], postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"})

    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alt_text", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_product_images_product_id", "product_images", ["product_id"])


def downgrade() -> None:
    op.drop_index("idx_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("idx_products_name_trgm", table_name="products")
    op.drop_index("idx_products_sku", table_name="products")
    op.drop_table("products")
