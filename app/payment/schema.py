from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.payment.enums import PaymentCurrencyEnum, PaymentStatusEnum
from app.payment.model import Payment


class ICreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: PaymentCurrencyEnum
    description: str | None = None
    metadata: dict | None = None
    webhook_url: HttpUrl


class IAccepted(BaseModel):
    payment_id: UUID
    status: PaymentStatusEnum
    created_at: datetime

    @classmethod
    def from_payment(cls, payment: Payment) -> "IAccepted":
        return cls(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )


class IRead(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: PaymentCurrencyEnum
    description: str | None
    metadata: dict | None
    status: PaymentStatusEnum
    idempotency_key: str
    webhook_url: str
    failure_reason: str | None
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_payment(cls, payment: Payment) -> "IRead":
        return cls(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.meta_data,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )


class ICreatePaymentDB(BaseModel):
    amount: Decimal
    currency: PaymentCurrencyEnum
    description: str | None = None
    meta_data: dict | None = None
    status: PaymentStatusEnum = PaymentStatusEnum.pending
    idempotency_key: str
    webhook_url: str
