from core.base.model import Base, BaseOutboxModel


__all__ = ("Outbox",)


class Outbox(BaseOutboxModel, Base):
    __tablename__ = "outbox"
