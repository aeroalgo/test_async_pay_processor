import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session
from sqlalchemy.orm import sessionmaker

from core.database.database import async_engine, job_async_engine


__all__ = (
    "get_session",
    "get_job_session",
    "async_session_factory",
    "job_async_session_factory",
)


_session_factory = sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

async_session_factory = async_scoped_session(
    _session_factory,
    scopefunc=lambda: id(asyncio.current_task()),
)

_job_session_factory = sessionmaker(
    bind=job_async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

job_async_session_factory = async_scoped_session(
    _job_session_factory,
    scopefunc=lambda: id(asyncio.current_task()),
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_job_session() -> AsyncGenerator[AsyncSession, None]:
    async with job_async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
