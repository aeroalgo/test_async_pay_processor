from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.model import BaseUUIDModel


ModelType = TypeVar("ModelType", bound=BaseUUIDModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db_session: AsyncSession, id: UUID) -> ModelType | None:
        result = await db_session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, db_session: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        data = obj_in.model_dump()
        db_obj = self.model(**data)
        db_session.add(db_obj)
        await db_session.flush()
        await db_session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db_session.add(db_obj)
        await db_session.flush()
        await db_session.refresh(db_obj)
        return db_obj
