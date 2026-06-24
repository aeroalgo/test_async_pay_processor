import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault(
    "POSTGRES_URI",
    "postgresql+asyncpg://payments:payments@localhost:5432/payments",
)
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("OUTBOX_POLL_INTERVAL_SEC", "60")

import sqlalchemy as sa

from core.database.session import get_session
from core.settings import get_settings

get_settings.cache_clear()


async def truncate_tables() -> None:
    async for db_session in get_session():
        await db_session.execute(
            sa.text("TRUNCATE TABLE outbox, payments RESTART IDENTITY CASCADE")
        )
        print("[done] Truncate payments, outbox")
        break


if __name__ == "__main__":
    asyncio.run(truncate_tables())
