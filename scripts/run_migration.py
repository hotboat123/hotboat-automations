"""Script temporal para ejecutar migración"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix para Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import DatabaseManager
from app.config import get_settings

async def run():
    db = DatabaseManager(get_settings().database_url)
    await db.initialize()
    
    migration_sql = Path('database/migrations/003_create_marketing_costs.sql').read_text(encoding='utf-8')
    
    # Ejecutar cada statement por separado
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(migration_sql)
    
    print('Tabla marketing_costs creada')
    await db.close()

if __name__ == "__main__":
    asyncio.run(run())
