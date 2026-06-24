from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.outbox.enums import OutboxStatusEnum


class ICreateOutboxDB(BaseModel):
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: dict
    status: OutboxStatusEnum = OutboxStatusEnum.pending
