import pytest

from unittest.mock import AsyncMock
from decimal import Decimal
from uuid import uuid4

from app.payment.enums import PaymentCurrencyEnum, PaymentStatusEnum
from app.payment.model import Payment
from consumer.handlers import PaymentProcessor


class StubGateway:
    def __init__(self, status: str = "succeeded", failure_reason: str | None = None):
        self.status = status
        self.failure_reason = failure_reason

    async def process(self) -> tuple[str, str | None]:
        return self.status, self.failure_reason


@pytest.mark.asyncio
async def test_processor_updates_payment_to_succeeded(db_session):
    payment = Payment(
        id=uuid4(),
        amount=Decimal("100.00"),
        currency=PaymentCurrencyEnum.RUB,
        status=PaymentStatusEnum.pending,
        idempotency_key="key-1",
        webhook_url="https://example.com/hook",
    )
    db_session.add(payment)
    await db_session.flush()

    webhook_sender = AsyncMock()
    processor = PaymentProcessor(
        gateway=StubGateway("succeeded"),
        webhook_sender=webhook_sender,
    )
    await processor.handle(db_session, {"payment_id": str(payment.id)})
    await db_session.refresh(payment)

    assert payment.status == PaymentStatusEnum.succeeded
    assert payment.processed_at is not None
    webhook_sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_processor_skips_non_pending_payment(db_session):
    payment = Payment(
        id=uuid4(),
        amount=Decimal("100.00"),
        currency=PaymentCurrencyEnum.RUB,
        status=PaymentStatusEnum.succeeded,
        idempotency_key="key-2",
        webhook_url="https://example.com/hook",
    )
    db_session.add(payment)
    await db_session.flush()

    webhook_sender = AsyncMock()
    processor = PaymentProcessor(gateway=StubGateway(), webhook_sender=webhook_sender)
    await processor.handle(db_session, {"payment_id": str(payment.id)})

    webhook_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_processor_marks_failed_when_gateway_fails(db_session):
    payment = Payment(
        id=uuid4(),
        amount=Decimal("50.00"),
        currency=PaymentCurrencyEnum.USD,
        status=PaymentStatusEnum.pending,
        idempotency_key="key-3",
        webhook_url="https://example.com/hook",
    )
    db_session.add(payment)
    await db_session.flush()

    webhook_sender = AsyncMock()
    processor = PaymentProcessor(
        gateway=StubGateway("failed", "gateway_declined"),
        webhook_sender=webhook_sender,
    )
    await processor.handle(db_session, {"payment_id": str(payment.id)})
    await db_session.refresh(payment)

    assert payment.status == PaymentStatusEnum.failed
    assert payment.failure_reason == "gateway_declined"


@pytest.mark.asyncio
async def test_processor_persists_final_status_when_webhook_fails(db_session):
    payment = Payment(
        id=uuid4(),
        amount=Decimal("75.00"),
        currency=PaymentCurrencyEnum.EUR,
        status=PaymentStatusEnum.pending,
        idempotency_key="key-4",
        webhook_url="https://example.com/hook",
    )
    db_session.add(payment)
    await db_session.flush()

    webhook_sender = AsyncMock()
    webhook_sender.send.side_effect = RuntimeError("webhook_down")
    processor = PaymentProcessor(
        gateway=StubGateway("succeeded"),
        webhook_sender=webhook_sender,
    )

    await processor.handle(db_session, {"payment_id": str(payment.id)})
    await db_session.refresh(payment)

    assert payment.status == PaymentStatusEnum.succeeded
    assert payment.processed_at is not None
