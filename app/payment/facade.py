from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.payment.schema import IAccepted, ICreate, IRead
from app.payment.service import PaymentService, PaymentServiceDep
from core.base.schema import IGetResponseBase, IPostResponseBase


class PaymentFacade:
    def __init__(self, service: PaymentService):
        self._service = service

    async def create(
        self,
        db_session: AsyncSession,
        *,
        idempotency_key: str,
        body: ICreate,
    ) -> IPostResponseBase[IAccepted]:
        payment = await self._service.create(
            db_session,
            idempotency_key=idempotency_key,
            body=body,
        )
        return IPostResponseBase[IAccepted](data=IAccepted.from_payment(payment))

    async def get(
        self,
        db_session: AsyncSession,
        *,
        payment_id: UUID,
    ) -> IGetResponseBase[IRead]:
        payment = await self._service.get(db_session, payment_id=payment_id)
        return IGetResponseBase[IRead](data=IRead.from_payment(payment))


async def get_payment_facade(service: PaymentServiceDep) -> PaymentFacade:
    return PaymentFacade(service)


PaymentFacadeDep = Annotated[PaymentFacade, Depends(get_payment_facade)]
