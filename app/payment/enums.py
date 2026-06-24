import enum


class PaymentCurrencyEnum(str, enum.Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
