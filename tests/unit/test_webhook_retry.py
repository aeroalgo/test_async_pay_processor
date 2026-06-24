import pytest
from unittest.mock import AsyncMock, patch

from consumer.webhook_sender import WebhookSender


@pytest.mark.asyncio
async def test_webhook_sender_retries_until_success():
    sender = WebhookSender()
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    client = AsyncMock()
    client.post = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), mock_response])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("consumer.webhook_sender.httpx.AsyncClient", return_value=client):
        with patch("asyncio.sleep", new=AsyncMock()):
            await sender.send("https://example.com/hook", {"payment_id": "1"})

    assert client.post.await_count == 3


@pytest.mark.asyncio
async def test_webhook_sender_raises_after_max_retries():
    sender = WebhookSender()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=Exception("fail"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("consumer.webhook_sender.httpx.AsyncClient", return_value=client):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(Exception, match="fail"):
                await sender.send("https://example.com/hook", {"payment_id": "1"})

    assert client.post.await_count == 3
