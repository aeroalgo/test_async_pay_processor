import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.outbox.model import Outbox
from core.database.session import get_session

pytestmark = pytest.mark.integration

PAYMENT_BODY = {
    "amount": "100.50",
    "currency": "RUB",
    "description": "Test payment",
    "metadata": {"order_id": "order-1"},
    "webhook_url": "https://example.com/webhook",
}


def _poll_until(assertion, *, timeout_sec: float = 20.0, interval_sec: float = 0.5):
    deadline = time.time() + timeout_sec
    last_error = None
    while time.time() < deadline:
        try:
            return assertion()
        except AssertionError as exc:
            last_error = exc
            time.sleep(interval_sec)
    if last_error is not None:
        raise last_error
    raise AssertionError("polling timed out without assertion result")


def test_create_payment_returns_202(test_client, api_headers):
    headers = {**api_headers, "Idempotency-Key": str(uuid4())}
    response = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    assert response.status_code == 202
    payload = response.json()
    data = payload["data"]
    assert "payment_id" in data
    assert data["status"] == "pending"
    assert "created_at" in data
    assert payload["message"]


def test_create_payment_without_api_key_returns_401(test_client):
    headers = {"Idempotency-Key": str(uuid4())}
    response = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    assert response.status_code == 401


def test_create_payment_without_idempotency_key_returns_422(test_client, api_headers):
    response = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=api_headers)
    assert response.status_code == 422


def test_create_payment_idempotent_returns_same_payment(test_client, api_headers):
    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    first = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    second = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["payment_id"] == second.json()["data"]["payment_id"]


def test_create_payment_same_key_different_body_returns_409(test_client, api_headers):
    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    first = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    assert first.status_code == 202
    other_body = {**PAYMENT_BODY, "amount": "200.00"}
    second = test_client.post("/api/v1/payments", json=other_body, headers=headers)
    assert second.status_code == 409


def test_get_payment_returns_details(test_client, api_headers):
    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    created = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    response = test_client.get(f"/api/v1/payments/{payment_id}", headers=api_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["payment_id"] == payment_id
    assert data["amount"] == PAYMENT_BODY["amount"]
    assert data["currency"] == PAYMENT_BODY["currency"]
    assert data["description"] == PAYMENT_BODY["description"]
    assert data["metadata"] == PAYMENT_BODY["metadata"]
    assert data["webhook_url"] == PAYMENT_BODY["webhook_url"]
    assert data["status"] == "pending"
    assert data["idempotency_key"] == idempotency_key
    assert "created_at" in data
    assert data["processed_at"] is None
    assert data["failure_reason"] is None


def test_get_payment_not_found_returns_404(test_client, api_headers):
    response = test_client.get(
        f"/api/v1/payments/{uuid4()}",
        headers=api_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_creates_outbox_record(test_client, api_headers):
    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    response = test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    assert response.status_code == 202
    payment_id = response.json()["data"]["payment_id"]

    async for db_session in get_session():
        result = await db_session.execute(
            select(Outbox).where(Outbox.aggregate_id == UUID(payment_id))
        )
        outbox_row = result.scalar_one_or_none()
        assert outbox_row is not None
        assert outbox_row.event_type == "payments.new"
        assert outbox_row.aggregate_type == "payment"
        assert outbox_row.status in {"pending", "published"}
        assert outbox_row.payload["payment_id"] == payment_id
        break


@pytest.mark.asyncio
async def test_create_payment_idempotent_does_not_duplicate_outbox(test_client, api_headers):
    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    test_client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)

    async for db_session in get_session():
        result = await db_session.execute(select(Outbox))
        outbox_rows = result.scalars().all()
        assert len(outbox_rows) == 1
        break


def test_payment_processing_retries_webhook_until_success(test_client, api_headers, webhook_base_url):
    hook_id = str(uuid4())
    configure_response = test_client.put(
        f"/api/v1/test-hooks/{hook_id}/config",
        headers=api_headers,
        json={"failures_before_success": 2},
    )
    assert configure_response.status_code == 200

    headers = {**api_headers, "Idempotency-Key": str(uuid4())}
    create_response = test_client.post(
        "/api/v1/payments",
        json={
            **PAYMENT_BODY,
            "webhook_url": f"{webhook_base_url}/api/v1/test-hooks/{hook_id}/deliver",
        },
        headers=headers,
    )
    assert create_response.status_code == 202
    payment_id = create_response.json()["data"]["payment_id"]

    def assert_processed():
        payment_response = test_client.get(
            f"/api/v1/payments/{payment_id}",
            headers=api_headers,
        )
        assert payment_response.status_code == 200
        payment = payment_response.json()["data"]
        assert payment["status"] in {"succeeded", "failed"}
        return payment

    payment = _poll_until(assert_processed, timeout_sec=25.0)

    def assert_hook_received():
        hook_response = test_client.get(
            f"/api/v1/test-hooks/{hook_id}",
            headers=api_headers,
        )
        assert hook_response.status_code == 200
        hook = hook_response.json()["data"]
        assert hook["attempts"] == 3
        assert hook["successful_deliveries"] == 1
        assert hook["last_payload"]["payment_id"] == payment_id
        assert hook["last_payload"]["status"] == payment["status"]
        return hook

    _poll_until(assert_hook_received, timeout_sec=25.0)


def test_payment_processing_stops_after_max_webhook_retries(test_client, api_headers, webhook_base_url):
    hook_id = str(uuid4())
    configure_response = test_client.put(
        f"/api/v1/test-hooks/{hook_id}/config",
        headers=api_headers,
        json={"failures_before_success": 10},
    )
    assert configure_response.status_code == 200

    headers = {**api_headers, "Idempotency-Key": str(uuid4())}
    create_response = test_client.post(
        "/api/v1/payments",
        json={
            **PAYMENT_BODY,
            "webhook_url": f"{webhook_base_url}/api/v1/test-hooks/{hook_id}/deliver",
        },
        headers=headers,
    )
    assert create_response.status_code == 202
    payment_id = create_response.json()["data"]["payment_id"]

    def assert_processed():
        payment_response = test_client.get(
            f"/api/v1/payments/{payment_id}",
            headers=api_headers,
        )
        assert payment_response.status_code == 200
        payment = payment_response.json()["data"]
        assert payment["status"] in {"succeeded", "failed"}
        return payment

    _poll_until(assert_processed, timeout_sec=25.0)

    def assert_hook_failed_after_retries():
        hook_response = test_client.get(
            f"/api/v1/test-hooks/{hook_id}",
            headers=api_headers,
        )
        assert hook_response.status_code == 200
        hook = hook_response.json()["data"]
        assert hook["attempts"] == 3
        assert hook["successful_deliveries"] == 0
        return hook

    _poll_until(assert_hook_failed_after_retries, timeout_sec=25.0)


def test_idempotent_create_triggers_single_webhook_delivery(test_client, api_headers, webhook_base_url):
    hook_id = str(uuid4())
    configure_response = test_client.put(
        f"/api/v1/test-hooks/{hook_id}/config",
        headers=api_headers,
        json={"failures_before_success": 0},
    )
    assert configure_response.status_code == 200

    idempotency_key = str(uuid4())
    headers = {**api_headers, "Idempotency-Key": idempotency_key}
    body = {
        **PAYMENT_BODY,
        "webhook_url": f"{webhook_base_url}/api/v1/test-hooks/{hook_id}/deliver",
    }
    first = test_client.post("/api/v1/payments", json=body, headers=headers)
    second = test_client.post("/api/v1/payments", json=body, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["payment_id"] == second.json()["data"]["payment_id"]
    payment_id = first.json()["data"]["payment_id"]

    def assert_hook_delivered_once():
        hook_response = test_client.get(
            f"/api/v1/test-hooks/{hook_id}",
            headers=api_headers,
        )
        assert hook_response.status_code == 200
        hook = hook_response.json()["data"]
        assert hook["attempts"] == 1
        assert hook["successful_deliveries"] == 1
        assert hook["last_payload"]["payment_id"] == payment_id
        return hook

    _poll_until(assert_hook_delivered_once, timeout_sec=25.0)
