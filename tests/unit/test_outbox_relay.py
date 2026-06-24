from unittest.mock import AsyncMock

import pytest

from app.outbox.service import OutboxRelayService


class FakePublisher:
    def __init__(self):
        self.published: list[dict] = []

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def publish_payment_new(self, payload: dict) -> None:
        self.published.append(payload)


@pytest.mark.asyncio
async def test_outbox_relay_publishes_pending_rows(db_session):
    from app.outbox.crud import outbox as outbox_crud
    from app.outbox.schema import ICreateOutboxDB
    from uuid import uuid4

    aggregate_id = uuid4()
    await outbox_crud.create(
        db_session,
        obj_in=ICreateOutboxDB(
            aggregate_type="payment",
            aggregate_id=aggregate_id,
            event_type="payments.new",
            payload={"payment_id": str(aggregate_id), "amount": "10.00"},
        ),
    )
    await db_session.commit()

    publisher = FakePublisher()
    relay = OutboxRelayService(publisher=publisher)
    count = await relay.relay_pending(db_session)
    await db_session.commit()

    assert count == 1
    assert len(publisher.published) == 1
    assert publisher.published[0]["payment_id"] == str(aggregate_id)
