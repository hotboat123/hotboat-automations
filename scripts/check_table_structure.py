"""
Script para ver la estructura real de la tabla booknetic_appointments
"""
import asyncio
import sys
from pathlib import Path

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


async def check_structure():
    """Verifica la estructura real de la tabla"""
    
    logger.info("🔍 Verificando estructura de booknetic_appointments...")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url, auto_setup=False)
    await db.initialize()
    
    try:
        # 1. Ver todas las columnas de la tabla
        logger.info("\n1️⃣ Columnas de la tabla:")
        query_columns = """
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = 'booknetic_appointments'
            ORDER BY ordinal_position
        """
        columns = await db.execute_query(query_columns)
        for col in columns:
            logger.info(f"   - {col.get('column_name')} ({col.get('data_type')}) - Nullable: {col.get('is_nullable')}")
        
        # 2. Ver una fila completa (raw)
        logger.info("\n2️⃣ Una fila completa (todas las columnas):")
        query_sample = """
            SELECT *
            FROM booknetic_appointments
            LIMIT 1
        """
        sample = await db.execute_query(query_sample)
        if sample:
            logger.info(f"   Columnas encontradas: {list(sample[0].keys())}")
            for key, value in sample[0].items():
                logger.info(f"   {key}: {value}")
        else:
            logger.info("   No hay filas en la tabla")
        
        # 3. Ver las últimas 3 filas con todos sus datos
        logger.info("\n3️⃣ Últimas 3 filas (todos los datos):")
        query_last = """
            SELECT *
            FROM booknetic_appointments
            ORDER BY id DESC
            LIMIT 3
        """
        last_rows = await db.execute_query(query_last)
        for i, row in enumerate(last_rows, 1):
            logger.info(f"\n   Fila {i}:")
            for key, value in row.items():
                logger.info(f"      {key}: {value}")
        
        # 4. Buscar columnas que puedan contener fechas
        logger.info("\n4️⃣ Buscando columnas con fechas:")
        query_dates = """
            SELECT 
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_name = 'booknetic_appointments'
              AND (data_type LIKE '%timestamp%' OR data_type LIKE '%date%')
        """
        date_cols = await db.execute_query(query_dates)
        for col in date_cols:
            logger.info(f"   - {col.get('column_name')} ({col.get('data_type')})")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(check_structure())



