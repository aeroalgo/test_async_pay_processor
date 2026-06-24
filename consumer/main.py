from faststream import FastStream
from faststream.rabbit import RabbitMessage

from consumer.handlers import PaymentProcessor
from core.database.session import job_async_session_factory
from core.logger import logger
from core.messaging.rabbit import (
    broker,
    dlx_exchange,
    payments_dlq,
    payments_exchange,
    payments_new_queue,
)

processor = PaymentProcessor()
app = FastStream(broker)

MAX_MESSAGE_RETRIES = 3


@broker.subscriber(payments_new_queue, exchange=payments_exchange)
async def on_payment_new(payload: dict, message: RabbitMessage) -> None:
    delivery_count = _get_delivery_count(message)
    try:
        async with job_async_session_factory() as db_session:
            await processor.handle(db_session, payload)
            await db_session.commit()
    except Exception:
        if delivery_count >= MAX_MESSAGE_RETRIES - 1:
            logger.error("payment message failed after retries, moving to DLQ: %s", payload)
        raise


@broker.subscriber(payments_dlq, exchange=dlx_exchange)
async def on_payment_dlq(payload: dict) -> None:
    logger.error("payment message in DLQ: %s", payload)


def _get_delivery_count(message: RabbitMessage) -> int:
    headers = message.headers or {}
    x_death = headers.get("x-death")
    if x_death:
        return sum(item.get("count", 0) for item in x_death)
    return int(headers.get("x-delivery-count", 0) or 0)
