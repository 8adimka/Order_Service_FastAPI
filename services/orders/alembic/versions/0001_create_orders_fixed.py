"""Create orders table - fixed version

Revision ID: 0001_create_orders_fixed
Revises:
Create Date: 2026-02-17 21:44:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_create_orders_fixed"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type using raw SQL with IF NOT EXISTS
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
                CREATE TYPE order_status AS ENUM ('PENDING', 'PAID', 'SHIPPED', 'CANCELED');
            END IF;
        END
        $$;
    """)

    # Create orders table
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "PAID", "SHIPPED", "CANCELED", name="order_status"
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create index
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")
    op.execute("DROP TYPE IF EXISTS order_status")
