import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.settings import settings

import app.model  # noqa: F401


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests requiring PostgreSQL")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "prepare_test_db.py")],
        check=False,
        cwd=str(Path(__file__).parent.parent),
    )
    if result.returncode != 0:
        raise RuntimeError("prepare_test_db failed")


async def _truncate_tables() -> None:
    engine = create_async_engine(settings.POSTGRES_URI, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("TRUNCATE TABLE outbox, payments RESTART IDENTITY CASCADE")
        )
    await engine.dispose()


@pytest.fixture(autouse=True)
def clean_payments_tables():
    asyncio.run(_truncate_tables())
    yield
    asyncio.run(_truncate_tables())


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(settings.POSTGRES_URI, poolclass=NullPool)
    return engine


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session
