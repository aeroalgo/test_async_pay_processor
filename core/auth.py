from typing import Annotated

from fastapi import Header

from core.exceptions import UnauthorizedException
from core.settings import settings


async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    if not x_api_key:
        raise UnauthorizedException("API key is required")
    if x_api_key != settings.API_KEY:
        raise UnauthorizedException("Invalid API key")
    return x_api_key
