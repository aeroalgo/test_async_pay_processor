import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.crud import outbox as outbox_crud
from core.database.session import job_async_session_factory
from core.logger import logger
from core.messaging.publisher import MessagePublisher
from core.messaging.rabbit import RabbitMQPublisher
from core.settings import settings


class OutboxRelayService:
    def __init__(self, publisher: MessagePublisher | None = None):
        self._publisher = publisher or RabbitMQPublisher()
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        await self._publisher.connect()
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.debug("outbox relay: started")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._publisher.close()
        logger.debug("outbox relay: stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.process_batch()
            except Exception as exc:
                logger.exception("outbox relay: batch failed: %s", exc)
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SEC)

    async def process_batch(self) -> None:
        async with job_async_session_factory() as db_session:
            rows = await outbox_crud.fetch_pending(db_session, limit=10)
            if not rows:
                return
            for row in rows:
                await self._publisher.publish_payment_new(row.payload)
                await outbox_crud.mark_published(db_session, outbox_id=row.id)
            await db_session.commit()

    async def relay_pending(self, db_session: AsyncSession) -> int:
        rows = await outbox_crud.fetch_pending(db_session, limit=10)
        for row in rows:
            await self._publisher.publish_payment_new(row.payload)
            await outbox_crud.mark_published(db_session, outbox_id=row.id)
        return len(rows)


_outbox_relay: OutboxRelayService | None = None


def get_outbox_relay() -> OutboxRelayService:
    global _outbox_relay
    if _outbox_relay is None:
        _outbox_relay = OutboxRelayService()
    return _outbox_relay
