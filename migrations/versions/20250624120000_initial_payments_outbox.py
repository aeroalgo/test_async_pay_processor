"""initial payments and outbox tables

Revision ID: 20250624120000
Revises:
Create Date: 2025-06-24 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20250624120000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payment_currency_enum = postgresql.ENUM(
    "RUB",
    "USD",
    "EUR",
    name="payment_currency_enum",
    create_type=False,
)
payment_status_enum = postgresql.ENUM(
    "pending",
    "succeeded",
    "failed",
    name="payment_status_enum",
    create_type=False,
)


def upgrade() -> None:
    payment_currency_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", payment_currency_enum, nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            payment_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("webhook_url", sa.String(length=2048), nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_payments_created_at"), "payments", ["created_at"], unique=False)
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_idempotency_key"), "payments", ["idempotency_key"], unique=False)
    op.create_index(op.f("ix_payments_updated_at"), "payments", ["updated_at"], unique=False)

    op.create_table(
        "outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_aggregate_id"), "outbox", ["aggregate_id"], unique=False)
    op.create_index(op.f("ix_outbox_created_at"), "outbox", ["created_at"], unique=False)
    op.create_index(op.f("ix_outbox_id"), "outbox", ["id"], unique=False)
    op.create_index(
        "ix_outbox_status_pending",
        "outbox",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_status_pending", table_name="outbox")
    op.drop_index(op.f("ix_outbox_id"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_created_at"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_aggregate_id"), table_name="outbox")
    op.drop_table("outbox")

    op.drop_index(op.f("ix_payments_updated_at"), table_name="payments")
    op.drop_index(op.f("ix_payments_idempotency_key"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_created_at"), table_name="payments")
    op.drop_table("payments")

    payment_status_enum.drop(op.get_bind(), checkfirst=True)
    payment_currency_enum.drop(op.get_bind(), checkfirst=True)
