import httpx
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from core.settings import settings


class WebhookSender:
    async def send(self, url: str, payload: dict) -> None:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(settings.WEBHOOK_MAX_RETRIES),
            wait=wait_exponential(
                multiplier=settings.WEBHOOK_RETRY_BASE_DELAY_SEC,
                min=settings.WEBHOOK_RETRY_BASE_DELAY_SEC,
                exp_base=2,
            ),
            reraise=True,
        )
        async with httpx.AsyncClient() as client:
            async for attempt in retrying:
                with attempt:
                    response = await client.post(url, json=payload, timeout=10.0)
                    response.raise_for_status()
