"""
Script para revisar y enviar el reporte de una fecha específica
Uso: python scripts/review_date_report.py 2026-03-21
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.logger import logger
from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.notifications.manager import NotificationManager


async def review_date(target_date_str: str = None):
    """Revisa y envía el reporte de una fecha específica"""
    
    # Si no se proporciona fecha, usar ayer
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Formato de fecha invalido: %s", target_date_str)
            logger.info("Formato correcto: YYYY-MM-DD (ej: 2026-03-21)")
            return
    else:
        target_date = datetime.now().date() - timedelta(days=1)
        logger.info("No se especifico fecha, usando ayer")
    
    logger.info("Revisando reporte del %s...", target_date.strftime('%d/%m/%Y'))
    
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones (config completo)
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        # Obtener datos desde reservas_con_extras
        logger.info("Obteniendo datos del dia...")
        summary_data = await monitor._get_daily_summary(target_date)
        marketing_cost = await monitor._get_marketing_cost(target_date)
        
        logger.info("Reservas del dia: %d", summary_data['total_reservas'])
        logger.info("  - Con info: %d", summary_data['reservas_con_info'])
        logger.info("  - Sin info: %d", summary_data['reservas_sin_info'])
        logger.info("Total ingresos: $%s", f"{summary_data['total_ingresos']:,.0f}")
        
        # Enviar reporte
        await monitor._send_daily_report(target_date, summary_data, marketing_cost)
        logger.info("Reporte enviado! Revisa tu Email")
        
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    
    await notification_manager.close()


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    if date_arg:
        logger.info("Fecha especificada: %s", date_arg)
    else:
        logger.info("Uso: python scripts/review_date_report.py YYYY-MM-DD")
        logger.info("Ejemplo: python scripts/review_date_report.py 2026-03-21")
        logger.info("Si no especificas fecha, se usara ayer")
    
    asyncio.run(review_date(date_arg))
