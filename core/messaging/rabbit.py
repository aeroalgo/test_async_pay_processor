from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from core.messaging.constants import (
    PAYMENTS_DLQ_ROUTING_KEY,
    PAYMENTS_DLX_EXCHANGE,
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_DLQ,
    PAYMENTS_NEW_QUEUE,
    PAYMENTS_NEW_ROUTING_KEY,
)
from core.messaging.publisher import MessagePublisher
from core.settings import settings


payments_exchange = RabbitExchange(
    PAYMENTS_EXCHANGE,
    type=ExchangeType.DIRECT,
    durable=True,
)

dlx_exchange = RabbitExchange(
    PAYMENTS_DLX_EXCHANGE,
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_new_queue = RabbitQueue(
    PAYMENTS_NEW_QUEUE,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_EXCHANGE,
        "x-dead-letter-routing-key": PAYMENTS_DLQ_ROUTING_KEY,
    },
)

payments_dlq = RabbitQueue(
    PAYMENTS_NEW_DLQ,
    durable=True,
    routing_key=PAYMENTS_DLQ_ROUTING_KEY,
)

broker = RabbitBroker(settings.RABBITMQ_URL)


class RabbitMQPublisher:
    def __init__(self, rabbit_broker: RabbitBroker | None = None):
        self._broker = rabbit_broker or broker
        self._publisher = None

    async def connect(self) -> None:
        await self._broker.connect()
        self._publisher = self._broker.publisher(
            queue=payments_new_queue,
            exchange=payments_exchange,
        )

    async def close(self) -> None:
        await self._broker.close()

    async def publish_payment_new(self, payload: dict) -> None:
        if self._publisher is None:
            raise RuntimeError("RabbitMQ publisher is not connected")
        await self._publisher.publish(payload)
