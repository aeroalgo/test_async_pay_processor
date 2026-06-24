import asyncio

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from core.base.model import Base
from core.logger import logger
from core.settings import settings


__all__ = (
    "Base",
    "async_engine",
    "job_async_engine",
    "get_engine_url",
    "init_database",
)


def get_engine_url() -> str:
    return settings.POSTGRES_URI


def _get_api_pool():
    return AsyncAdaptedQueuePool if settings.ENVIRONMENT == "testing" else NullPool


async_engine: AsyncEngine = create_async_engine(
    url=get_engine_url(),
    echo=False,
    poolclass=_get_api_pool(),
)

job_async_engine: AsyncEngine = create_async_engine(
    url=get_engine_url(),
    echo=False,
    pool_size=10,
    max_overflow=5,
    poolclass=AsyncAdaptedQueuePool,
)


async def db_test_connection(engine: AsyncEngine) -> None:
    for attempt in range(3):
        try:
            async with engine.begin() as conn:
                await conn.execute(select(1))
            logger.debug("database: connection success")
            return
        except Exception as exc:
            logger.error("database: attempt %s connection failed: %s", attempt, exc)
            await asyncio.sleep(1)
    raise RuntimeError("database: connection failed")


async def init_database() -> None:
    await db_test_connection(async_engine)
