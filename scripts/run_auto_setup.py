import asyncio
import sys

from app.config import get_settings
from app.database import DatabaseManager


async def main() -> None:
    settings = get_settings()
    db = DatabaseManager(
        settings.database_url,
        auto_setup=True,
    )
    await db.initialize()
    await db.close()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

