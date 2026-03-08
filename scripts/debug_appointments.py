"""
Script para diagnosticar por qué no encuentra las reservas
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.logger import logger
from app.database import DatabaseManager


async def debug_appointments():
    """Diagnostica las reservas del 18/11/2025"""
    
    logger.info("🔍 Diagnosticando reservas del 18/11/2025...")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url, auto_setup=False)
    await db.initialize()
    
    target_date = datetime(2025, 11, 18).date()
    
    try:
        # 1. Verificar que la tabla existe
        logger.info("\n1️⃣ Verificando que la tabla existe...")
        check_table = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'booknetic_appointments'
            ) as exists
        """
        result = await db.execute_single(check_table)
        logger.info(f"   Tabla existe: {result.get('exists') if result else False}")
        
        # 2. Contar TODAS las reservas (sin filtro de fecha)
        logger.info("\n2️⃣ Contando TODAS las reservas...")
        count_all = "SELECT COUNT(*) as total FROM booknetic_appointments"
        result = await db.execute_single(count_all)
        logger.info(f"   Total de reservas en la tabla: {result.get('total') if result else 0}")
        
        # 3. Ver las últimas 5 reservas con sus fechas
        logger.info("\n3️⃣ Últimas 5 reservas (con fechas):")
        last_reservations = """
            SELECT 
                id,
                customer_name,
                starts_at,
                DATE(starts_at) as fecha,
                status,
                created_at
            FROM booknetic_appointments
            ORDER BY starts_at DESC
            LIMIT 5
        """
        rows = await db.execute_query(last_reservations)
        for row in rows:
            logger.info(f"   - {row.get('customer_name')} | {row.get('starts_at')} | Fecha: {row.get('fecha')} | Status: {row.get('status')}")
        
        # 4. Buscar reservas del 18/11/2025 con diferentes formatos
        logger.info(f"\n4️⃣ Buscando reservas del {target_date}...")
        
        # Formato 1: DATE(starts_at) = date
        query1 = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE DATE(starts_at) = %s
        """
        result1 = await db.execute_single(query1, (target_date,))
        logger.info(f"   Con DATE(starts_at) = date: {result1.get('total') if result1 else 0}")
        
        # Formato 2: starts_at::date = date
        query2 = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE starts_at::date = %s
        """
        result2 = await db.execute_single(query2, (target_date,))
        logger.info(f"   Con starts_at::date = date: {result2.get('total') if result2 else 0}")
        
        # Formato 3: Rango de fechas (todo el día)
        query3 = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE starts_at >= %s::timestamp
              AND starts_at < (%s::date + INTERVAL '1 day')::timestamp
        """
        result3 = await db.execute_single(query3, (target_date, target_date))
        logger.info(f"   Con rango de timestamps: {result3.get('total') if result3 else 0}")
        
        # 5. Ver TODAS las reservas del 18/11/2025 (sin filtro de status)
        logger.info(f"\n5️⃣ Todas las reservas del {target_date} (incluyendo canceladas):")
        query_all = """
            SELECT 
                id,
                customer_name,
                starts_at,
                status,
                DATE(starts_at) as fecha
            FROM booknetic_appointments
            WHERE DATE(starts_at) = %s
            ORDER BY starts_at
        """
        rows_all = await db.execute_query(query_all, (target_date,))
        logger.info(f"   Total encontradas: {len(rows_all)}")
        for row in rows_all:
            logger.info(f"   - {row.get('customer_name')} | {row.get('starts_at')} | Status: {row.get('status')}")
        
        # 6. Ver reservas del 18/11/2025 SIN canceladas/rechazadas
        logger.info(f"\n6️⃣ Reservas del {target_date} (sin canceladas/rechazadas):")
        query_active = """
            SELECT 
                id,
                customer_name,
                starts_at,
                status
            FROM booknetic_appointments
            WHERE DATE(starts_at) = %s
              AND status NOT IN ('canceled', 'rejected')
            ORDER BY starts_at
        """
        rows_active = await db.execute_query(query_active, (target_date,))
        logger.info(f"   Total activas: {len(rows_active)}")
        for row in rows_active:
            logger.info(f"   - {row.get('customer_name')} | {row.get('starts_at')} | Status: {row.get('status')}")
        
        # 7. Verificar zona horaria de la base de datos
        logger.info("\n7️⃣ Verificando zona horaria de la BD:")
        query_tz = "SELECT current_setting('timezone') as timezone"
        result_tz = await db.execute_single(query_tz)
        logger.info(f"   Zona horaria: {result_tz.get('timezone') if result_tz else 'N/A'}")
        
        # 8. Verificar formato de starts_at
        logger.info("\n8️⃣ Verificando formato de starts_at:")
        query_format = """
            SELECT 
                starts_at,
                pg_typeof(starts_at) as tipo,
                EXTRACT(TIMEZONE FROM starts_at) as timezone_offset
            FROM booknetic_appointments
            ORDER BY starts_at DESC
            LIMIT 1
        """
        result_format = await db.execute_single(query_format)
        if result_format:
            logger.info(f"   Tipo: {result_format.get('tipo')}")
            logger.info(f"   Ejemplo: {result_format.get('starts_at')}")
            logger.info(f"   Offset timezone: {result_format.get('timezone_offset')}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(debug_appointments())

