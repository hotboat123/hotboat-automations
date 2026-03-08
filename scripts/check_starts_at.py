"""
Script para verificar específicamente la columna starts_at
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.logger import logger
from app.database import DatabaseManager


async def check_starts_at():
    """Verifica específicamente starts_at"""
    
    logger.info("🔍 Verificando columna starts_at...")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url, auto_setup=False)
    await db.initialize()
    
    try:
        # 1. Verificar si starts_at existe y tiene valores
        logger.info("\n1️⃣ Verificando starts_at:")
        query_check = """
            SELECT 
                COUNT(*) as total,
                COUNT(starts_at) as con_starts_at,
                COUNT(*) - COUNT(starts_at) as sin_starts_at
            FROM booknetic_appointments
        """
        result = await db.execute_single(query_check)
        logger.info(f"   Total filas: {result.get('total')}")
        logger.info(f"   Con starts_at: {result.get('con_starts_at')}")
        logger.info(f"   Sin starts_at (NULL): {result.get('sin_starts_at')}")
        
        # 2. Ver las últimas 10 filas con starts_at
        logger.info("\n2️⃣ Últimas 10 filas con starts_at:")
        query_last = """
            SELECT 
                id,
                starts_at,
                DATE(starts_at) as fecha,
                customer_name,
                status
            FROM booknetic_appointments
            WHERE starts_at IS NOT NULL
            ORDER BY starts_at DESC
            LIMIT 10
        """
        rows = await db.execute_query(query_last)
        logger.info(f"   Encontradas: {len(rows)}")
        for row in rows:
            logger.info(f"   - ID: {row.get('id')} | starts_at: {row.get('starts_at')} | Fecha: {row.get('fecha')} | Cliente: {row.get('customer_name')} | Status: {row.get('status')}")
        
        # 3. Buscar específicamente el 18/11/2025
        logger.info("\n3️⃣ Buscando reservas del 18/11/2025:")
        target_date = datetime(2025, 11, 18).date()
        
        # Forma 1: DATE(starts_at)
        query1 = """
            SELECT 
                id,
                starts_at,
                DATE(starts_at) as fecha,
                customer_name,
                status
            FROM booknetic_appointments
            WHERE starts_at IS NOT NULL
              AND DATE(starts_at) = %s
            ORDER BY starts_at
        """
        rows1 = await db.execute_query(query1, (target_date,))
        logger.info(f"   Con DATE(starts_at) = {target_date}: {len(rows1)} reservas")
        for row in rows1:
            logger.info(f"   - {row.get('customer_name')} | {row.get('starts_at')} | Status: {row.get('status')}")
        
        # Forma 2: Rango completo del día (considerando timezone)
        logger.info(f"\n4️⃣ Buscando en rango del día (00:00 a 23:59 UTC):")
        query2 = """
            SELECT 
                id,
                starts_at,
                DATE(starts_at) as fecha,
                customer_name,
                status
            FROM booknetic_appointments
            WHERE starts_at IS NOT NULL
              AND starts_at >= %s::timestamp
              AND starts_at < (%s::date + INTERVAL '1 day')::timestamp
            ORDER BY starts_at
        """
        rows2 = await db.execute_query(query2, (target_date, target_date))
        logger.info(f"   En rango: {len(rows2)} reservas")
        for row in rows2:
            logger.info(f"   - {row.get('customer_name')} | {row.get('starts_at')} | Status: {row.get('status')}")
        
        # 5. Ver todas las fechas únicas en starts_at
        logger.info("\n5️⃣ Fechas únicas en starts_at (últimas 10):")
        query_dates = """
            SELECT DISTINCT DATE(starts_at) as fecha, COUNT(*) as cantidad
            FROM booknetic_appointments
            WHERE starts_at IS NOT NULL
            GROUP BY DATE(starts_at)
            ORDER BY fecha DESC
            LIMIT 10
        """
        dates = await db.execute_query(query_dates)
        for date_row in dates:
            logger.info(f"   - {date_row.get('fecha')}: {date_row.get('cantidad')} reservas")
        
        # 6. Verificar si hay reservas cerca del 18/11 (17, 18, 19)
        logger.info("\n6️⃣ Reservas del 17, 18 y 19 de noviembre:")
        query_range = """
            SELECT 
                DATE(starts_at) as fecha,
                COUNT(*) as cantidad
            FROM booknetic_appointments
            WHERE starts_at IS NOT NULL
              AND DATE(starts_at) BETWEEN '2025-11-17' AND '2025-11-19'
            GROUP BY DATE(starts_at)
            ORDER BY fecha
        """
        range_dates = await db.execute_query(query_range)
        for date_row in range_dates:
            logger.info(f"   - {date_row.get('fecha')}: {date_row.get('cantidad')} reservas")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(check_starts_at())


