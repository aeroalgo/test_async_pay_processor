from pydantic import BaseModel
from uuid import UUID


class PaymentNewEvent(BaseModel):
    payment_id: UUID
    amount: str
    currency: str
    webhook_url: str
