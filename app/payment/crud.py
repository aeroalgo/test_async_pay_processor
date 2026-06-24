from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payment.model import Payment
from app.payment.schema import ICreatePaymentDB
from core.base.crud import CRUDBase


class CRUD(CRUDBase[Payment, ICreatePaymentDB, object]):
    async def get_by_idempotency_key(
        self,
        db_session: AsyncSession,
        *,
        idempotency_key: str,
    ) -> Payment | None:
        result = await db_session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()


payment = CRUD(Payment)
