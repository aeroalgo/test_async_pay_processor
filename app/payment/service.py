from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.crud import outbox as outbox_crud
from app.outbox.schema import ICreateOutboxDB
from app.payment.crud import payment as payment_crud
from app.payment.enums import PaymentStatusEnum
from app.payment.model import Payment
from app.payment.schema import ICreate, ICreatePaymentDB
from core.exceptions import ConflictException, NotFoundException


class PaymentService:
    async def create(
        self,
        db_session: AsyncSession,
        *,
        idempotency_key: str,
        body: ICreate,
    ) -> Payment:
        existing = await payment_crud.get_by_idempotency_key(
            db_session,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            if not self._matches_body(existing, body):
                raise ConflictException("Idempotency key reused with different request body")
            return existing

        try:
            payment_obj = await payment_crud.create(
                db_session,
                obj_in=ICreatePaymentDB(
                    amount=body.amount,
                    currency=body.currency,
                    description=body.description,
                    meta_data=body.metadata,
                    status=PaymentStatusEnum.pending,
                    idempotency_key=idempotency_key,
                    webhook_url=str(body.webhook_url),
                ),
            )
            await outbox_crud.create(
                db_session,
                obj_in=ICreateOutboxDB(
                    aggregate_type="payment",
                    aggregate_id=payment_obj.id,
                    event_type="payments.new",
                    payload={
                        "payment_id": str(payment_obj.id),
                        "amount": str(payment_obj.amount),
                        "currency": payment_obj.currency.value,
                        "webhook_url": payment_obj.webhook_url,
                    },
                ),
            )
            return payment_obj
        except IntegrityError:
            await db_session.rollback()
            existing = await payment_crud.get_by_idempotency_key(
                db_session,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            if not self._matches_body(existing, body):
                raise ConflictException("Idempotency key reused with different request body")
            return existing

    async def get(self, db_session: AsyncSession, *, payment_id: UUID) -> Payment:
        payment_obj = await payment_crud.get(db_session, payment_id)
        if payment_obj is None:
            raise NotFoundException("Payment not found")
        return payment_obj

    @staticmethod
    def _matches_body(payment_obj: Payment, body: ICreate) -> bool:
        return (
            payment_obj.amount == body.amount
            and payment_obj.currency == body.currency
            and payment_obj.description == body.description
            and payment_obj.meta_data == body.metadata
            and payment_obj.webhook_url == str(body.webhook_url)
        )

async def get_payment_service() -> PaymentService:
    return PaymentService()


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
