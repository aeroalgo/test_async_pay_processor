import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa

from core.database.session import get_session


async def truncate_tables() -> None:
    async for db_session in get_session():
        await db_session.execute(
            sa.text("TRUNCATE TABLE outbox, payments RESTART IDENTITY CASCADE")
        )
        print("[done] Truncate payments, outbox")
        break


if __name__ == "__main__":
    asyncio.run(truncate_tables())
