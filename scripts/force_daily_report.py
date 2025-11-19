"""
Script para forzar el envío del reporte diario inmediatamente
Útil para pruebas sin esperar a las 9 AM
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
from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.notifications.manager import NotificationManager


async def force_report():
    """Fuerza el envío del reporte inmediatamente"""
    
    logger.info("🚀 Forzando envío de reporte diario...")
    
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    # Esperar un poco
    await asyncio.sleep(2)
    
    # Obtener datos de ayer
    yesterday = datetime.now().date() - timedelta(days=1)
    
    logger.info(f"📅 Analizando reservas del {yesterday.strftime('%d/%m/%Y')}...")
    
    try:
        # Contar reservas
        appointments_count = await monitor._count_appointments(yesterday)
        logger.info(f"✅ Reservas encontradas: {appointments_count}")
        
        # Contar información
        info_count = await monitor._count_info_reservas(yesterday)
        logger.info(f"✅ Información completada: {info_count}")
        
        # Obtener faltantes
        missing = await monitor._get_missing_reservas(yesterday)
        logger.info(f"⚠️  Reservas faltantes: {len(missing)}")
        
        # Enviar reporte
        logger.info("📤 Enviando reporte por WhatsApp y Email...")
        await monitor._send_daily_report(yesterday, appointments_count, info_count, missing)
        
        logger.info("✅ Reporte enviado! Revisa WhatsApp y Email")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    
    await notification_manager.close()


if __name__ == "__main__":
    asyncio.run(force_report())

