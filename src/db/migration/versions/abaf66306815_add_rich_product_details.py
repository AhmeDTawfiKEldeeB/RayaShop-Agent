"""add rich product details

Revision ID: <GENERATED_REVISION_ID>
Revises: 61a875b563fe
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "<GENERATED_REVISION_ID>"
down_revision: str | None = "61a875b563fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.add_column(
        "products",
        sa.Column(
            "brand",
            sa.String(255),
            nullable=True,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "category",
            sa.String(255),
            nullable=True,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "short_description",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=True,
        ),
    )

    op.create_index(
        "idx_products_brand",
        "products",
        ["brand"],
    )

    op.create_index(
        "idx_products_category",
        "products",
        ["category"],
    )


def downgrade() -> None:

    op.drop_index(
        "idx_products_category",
        table_name="products",
    )

    op.drop_index(
        "idx_products_brand",
        table_name="products",
    )

    op.drop_column(
        "products",
        "attributes",
    )

    op.drop_column(
        "products",
        "short_description",
    )

    op.drop_column(
        "products",
        "description",
    )

    op.drop_column(
        "products",
        "category",
    )

    op.drop_column(
        "products",
        "brand",
    )