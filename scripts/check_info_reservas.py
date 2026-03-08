"""
Script para revisar datos en Información Reservas sin cruzar
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.database import DatabaseManager
from app.logger import logger


async def check_info_reservas(target_date_str: str):
    """Revisa datos en Información Reservas para una fecha específica"""
    
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Formato de fecha inválido: {target_date_str}")
        logger.info("Formato correcto: YYYY-MM-DD (ej: 2026-01-15)")
        return
    
    logger.info(f"Revisando 'Información Reservas' para {target_date.strftime('%d/%m/%Y')}...")
    
    settings = get_settings()
    db = DatabaseManager(settings)
    await db.initialize()
    
    # Query para obtener todos los registros
    query = r"""
        SELECT 
            ir.id,
            ir.created_at,
            ir.updated_at,
            ir.raw->>'fecha' AS fecha_formulario,
            ir.raw->>'nombre_cliente' AS nombre_cliente,
            ir.raw->>'telefono' AS telefono,
            ir.raw->>'horario_salida' AS horario_salida,
            ir.raw->>'hora_salida' AS hora_salida,
            ir.raw->>'productos' AS productos,
            ir.raw,
            CASE
                WHEN ir.raw ? 'fecha'
                     AND NULLIF(ir.raw->>'fecha', '') IS NOT NULL
                     AND ir.raw->>'fecha' ~ '^\d{2}/\d{2}/\d{4}$'
                THEN to_date(ir.raw->>'fecha', 'DD/MM/YYYY')
                ELSE DATE(ir.created_at)
            END AS target_date
        FROM "Informacion Reservas" ir
        WHERE (
            CASE
                WHEN ir.raw ? 'fecha'
                     AND NULLIF(ir.raw->>'fecha', '') IS NOT NULL
                     AND ir.raw->>'fecha' ~ '^\d{2}/\d{2}/\d{4}$'
                THEN to_date(ir.raw->>'fecha', 'DD/MM/YYYY')
                ELSE DATE(ir.created_at)
            END
        ) = %s
        ORDER BY ir.created_at ASC
    """
    
    try:
        rows = await db.execute_query(query, (target_date,))
        
        if not rows:
            logger.info(f"No se encontraron registros en 'Información Reservas' para {target_date.strftime('%d/%m/%Y')}")
        else:
            logger.info(f"\nEncontrados {len(rows)} registros en 'Información Reservas':")
            logger.info("="*80)
            
            for idx, row in enumerate(rows, 1):
                logger.info(f"\n#{idx} ID: {row.get('id')}")
                logger.info(f"   Cliente: {row.get('nombre_cliente') or 'N/A'}")
                logger.info(f"   Teléfono: {row.get('telefono') or 'N/A'}")
                logger.info(f"   Fecha formulario: {row.get('fecha_formulario') or 'N/A'}")
                logger.info(f"   Horario salida: {row.get('horario_salida') or 'N/A'}")
                logger.info(f"   Hora salida: {row.get('hora_salida') or 'N/A'}")
                logger.info(f"   Productos: {row.get('productos') or 'N/A'}")
                logger.info(f"   Created at: {row.get('created_at')}")
                logger.info(f"   Target date (calculado): {row.get('target_date')}")
                
                # Mostrar campos con 'extra' en el nombre
                raw_data = row.get('raw', {})
                if isinstance(raw_data, str):
                    try:
                        raw_data = json.loads(raw_data)
                    except:
                        raw_data = {}
                
                extras_found = []
                for key, value in raw_data.items():
                    if 'extra' in key.lower() or 'cerveza' in key.lower() or 'bebida' in key.lower():
                        if value:
                            extras_found.append(f"{key}: {value}")
                
                if extras_found:
                    logger.info(f"   Extras detectados:")
                    for extra in extras_found:
                        logger.info(f"      - {extra}")
                else:
                    logger.info(f"   Extras detectados: Ninguno")
                
                logger.info("   " + "-"*76)
            
            logger.info("\n" + "="*80)
    
    except Exception as e:
        logger.error(f"Error consultando la base de datos: {e}", exc_info=True)
    
    await db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Uso: python scripts/check_info_reservas.py YYYY-MM-DD")
        logger.info("Ejemplo: python scripts/check_info_reservas.py 2026-01-15")
        sys.exit(1)
    
    date_arg = sys.argv[1]
    asyncio.run(check_info_reservas(date_arg))
