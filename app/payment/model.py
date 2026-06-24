from sqlalchemy import Column, Enum, Numeric, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from app.payment.enums import PaymentCurrencyEnum, PaymentStatusEnum
from core.base.model import Base, BaseUUIDModel


__all__ = ("Payment", "PaymentBase")


class PaymentBase:
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(
        Enum(PaymentCurrencyEnum, name="payment_currency_enum"),
        nullable=False,
    )
    description = Column(String(1024), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    status = Column(
        Enum(PaymentStatusEnum, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatusEnum.pending,
    )
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    webhook_url = Column(String(2048), nullable=False)
    failure_reason = Column(String(500), nullable=True)
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)


class Payment(PaymentBase, BaseUUIDModel, Base):
    __tablename__ = "payments"
