from sqlalchemy import TIMESTAMP, Column, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUID_PG
from sqlalchemy.orm import declarative_base


Base = declarative_base()

__all__ = (
    "Base",
    "BaseUUIDModel",
    "BaseOutboxModel",
)


class BaseUUIDModel:
    id = Column(
        UUID_PG(as_uuid=True),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()"),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        index=True,
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        index=True,
        server_default=func.now(),
    )


class BaseOutboxModel:
    id = Column(
        UUID_PG(as_uuid=True),
        primary_key=True,
        index=True,
        server_default=text("gen_random_uuid()"),
    )
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(128), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(32), nullable=False, server_default=text("'pending'"))
    created_at = Column(
        TIMESTAMP(timezone=True),
        index=True,
        server_default=func.now(),
    )
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
