import enum


class OutboxStatusEnum(str, enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"
