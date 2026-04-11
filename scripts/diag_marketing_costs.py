"""Diagnóstico: columnas, vistas, muestra de marketing_costs y fetch_marketing_for_date."""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Raíz del repo (scripts/ -> padre)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import DatabaseManager
from app.utils.marketing_costs import fetch_marketing_for_date


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no está definida (ni en entorno ni en .env).")
        return

    db = DatabaseManager(url, auto_setup=False)
    await db.initialize()

    cols = await db.execute_query(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'marketing_costs'
        ORDER BY ordinal_position
        """
    )
    print("=== Columnas marketing_costs ===")
    for r in cols:
        print(f"  {r['column_name']}: {r['data_type']}")

    views = await db.execute_query(
        """
        SELECT table_name FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name IN ('marketing_costs_daily', 'daily_marketing_summary')
        """
    )
    print("=== Vistas encontradas ===", [v["table_name"] for v in views])

    cnt = await db.execute_single("SELECT COUNT(*)::bigint AS n FROM marketing_costs")
    print("=== Filas en marketing_costs ===", cnt)

    sample = await db.execute_query("SELECT * FROM marketing_costs ORDER BY 1 DESC LIMIT 15")
    print("=== Últimas filas (hasta 15) ===")
    for row in sample:
        print(row)

    d = date(2026, 4, 10)
    m = await fetch_marketing_for_date(db, d)
    print("=== fetch_marketing_for_date(2026-04-10) ===", m)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
