from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.payment.facade import PaymentFacadeDep
from app.payment.schema import IAccepted, ICreate, IRead
from core.auth import verify_api_key
from core.base.schema import IGetResponseBase, IPostResponseBase
from core.dependencies import AsyncSession, get_session

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "",
    response_model=IPostResponseBase[IAccepted],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment(
    body: ICreate,
    facade: PaymentFacadeDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    db_session: AsyncSession = Depends(get_session),
):
    return await facade.create(
        db_session,
        idempotency_key=idempotency_key,
        body=body,
    )


@router.get("/{payment_id}", response_model=IGetResponseBase[IRead])
async def get_payment(
    payment_id: UUID,
    facade: PaymentFacadeDep,
    db_session: AsyncSession = Depends(get_session),
):
    return await facade.get(db_session, payment_id=payment_id)
