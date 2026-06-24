from typing import Generic, TypeVar

from pydantic import BaseModel


DataT = TypeVar("DataT")


class IResponseBase(BaseModel, Generic[DataT]):
    message: str = ""
    meta: dict = {}
    data: DataT | list[DataT] | None = None


class IGetResponseBase(IResponseBase[DataT], Generic[DataT]):
    message: str = "Данные успешно получены"


class IPostResponseBase(IResponseBase[DataT], Generic[DataT]):
    message: str = "Данные успешно добавлены"
