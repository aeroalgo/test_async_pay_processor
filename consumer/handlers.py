from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.payment.crud import payment as payment_crud
from app.payment.enums import PaymentStatusEnum
from consumer.payment_gateway import PaymentGateway, RandomPaymentGateway
from consumer.webhook_sender import WebhookSender
from core.logger import logger


class PaymentProcessor:
    def __init__(
        self,
        gateway: PaymentGateway | None = None,
        webhook_sender: WebhookSender | None = None,
    ):
        self._gateway = gateway or RandomPaymentGateway()
        self._webhook_sender = webhook_sender or WebhookSender()

    async def handle(self, db_session: AsyncSession, payload: dict) -> None:
        payment_id = UUID(payload["payment_id"])
        payment = await payment_crud.get(db_session, payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")
        if payment.status != PaymentStatusEnum.pending:
            return

        status_value, failure_reason = await self._gateway.process()
        payment.status = PaymentStatusEnum(status_value)
        payment.failure_reason = failure_reason
        payment.processed_at = datetime.now(timezone.utc)
        await db_session.flush()

        webhook_payload = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "amount": str(payment.amount),
            "currency": payment.currency.value,
            "processed_at": payment.processed_at.isoformat(),
        }
        try:
            await self._webhook_sender.send(payment.webhook_url, webhook_payload)
        except Exception as exc:
            logger.error("webhook delivery failed for payment %s: %s", payment.id, exc)
