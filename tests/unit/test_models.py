import app.model  # noqa: F401
from app.outbox.model import Outbox
from app.payment.enums import PaymentCurrencyEnum, PaymentStatusEnum
from app.payment.model import Payment
from core.base.model import Base


def test_payment_table_registered():
    assert "payments" in Base.metadata.tables


def test_outbox_table_registered():
    assert "outbox" in Base.metadata.tables


def test_payment_columns():
    columns = {column.name for column in Payment.__table__.columns}
    expected = {
        "id",
        "amount",
        "currency",
        "description",
        "meta_data",
        "status",
        "idempotency_key",
        "webhook_url",
        "failure_reason",
        "processed_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns)


def test_payment_idempotency_key_unique():
    idempotency_key_column = Payment.__table__.c.idempotency_key
    assert idempotency_key_column.unique is True


def test_payment_currency_enum_values():
    assert {item.value for item in PaymentCurrencyEnum} == {"RUB", "USD", "EUR"}


def test_payment_status_enum_values():
    assert {item.value for item in PaymentStatusEnum} == {"pending", "succeeded", "failed"}


def test_outbox_columns():
    columns = {column.name for column in Outbox.__table__.columns}
    expected = {
        "id",
        "aggregate_type",
        "aggregate_id",
        "event_type",
        "payload",
        "status",
        "created_at",
        "published_at",
    }
    assert columns == expected
