from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.enums import OutboxStatusEnum
from app.outbox.model import Outbox
from app.outbox.schema import ICreateOutboxDB
from core.base.crud import CRUDBase


class CRUD(CRUDBase[Outbox, ICreateOutboxDB, object]):
    async def fetch_pending(
        self,
        db_session: AsyncSession,
        *,
        limit: int = 10,
    ) -> Sequence[Outbox]:
        result = await db_session.execute(
            select(Outbox)
            .where(Outbox.status == OutboxStatusEnum.pending.value)
            .order_by(Outbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.scalars().all()

    async def mark_published(
        self,
        db_session: AsyncSession,
        *,
        outbox_id,
    ) -> None:
        await db_session.execute(
            update(Outbox)
            .where(Outbox.id == outbox_id)
            .values(
                status=OutboxStatusEnum.published.value,
                published_at=datetime.now(timezone.utc),
            )
        )


outbox = CRUD(Outbox)
