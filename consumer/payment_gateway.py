import asyncio
import random
from typing import Protocol


class PaymentGateway(Protocol):
    async def process(self) -> tuple[str, str | None]: ...


class RandomPaymentGateway:
    async def process(self) -> tuple[str, str | None]:
        await asyncio.sleep(random.uniform(2, 5))
        if random.random() < 0.9:
            return "succeeded", None
        return "failed", "gateway_declined"
