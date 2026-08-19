"""remove images column from products

Revision ID: 61a875b563fe
Revises: 23ce02c69b3f
Create Date: 2026-08-19 13:59:09.324244
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "61a875b563fe"
down_revision: Union[str, None] = "23ce02c69b3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("products", "images")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "images",
            sa.JSON(),
            nullable=True,
        ),
    )