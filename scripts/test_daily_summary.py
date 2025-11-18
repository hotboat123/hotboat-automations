"""
Script para probar el Monitor de Resumen Diario inmediatamente
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Fix para Windows: usar WindowsSelectorEventLoopPolicy
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.logger import logger
from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.notifications.manager import NotificationManager


async def test_daily_summary():
    """Ejecuta el reporte diario inmediatamente para pruebas"""
    
    logger.info("🧪 Iniciando prueba del Monitor de Resumen Diario...")
    
    # Configuración
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones
    notification_manager = NotificationManager(
        settings=settings,
        config=config
    )
    await notification_manager.initialize()
    
    # Crear el monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(
        settings=settings,
        config=monitor_config,
        notification_manager=notification_manager
    )
    
    # Inicializar el monitor
    await monitor.initialize()
    
    logger.info("📊 Generando reporte de prueba...")
    
    try:
        # Esperar un poco para que el pool de conexiones se inicialice
        await asyncio.sleep(2)
        
        # Obtener datos de ayer
        yesterday = datetime.now().date() - timedelta(days=1)
        logger.info(f"📅 Analizando reservas del día: {yesterday.strftime('%d/%m/%Y')}")
        
        # Contar reservas de ayer
        logger.info("🔍 Contando reservas en appointments...")
        appointments_count = await monitor._count_appointments(yesterday)
        logger.info(f"📅 Reservas de ayer: {appointments_count}")
        
        # Contar información completada
        logger.info("🔍 Contando información completada...")
        info_count = await monitor._count_info_reservas(yesterday)
        logger.info(f"📝 Información completada: {info_count}")
        
        # Obtener reservas faltantes
        logger.info("🔍 Buscando reservas faltantes...")
        missing = await monitor._get_missing_reservas(yesterday)
        logger.info(f"⚠️  Reservas faltantes: {len(missing)}")
        
        if missing:
            logger.info("📋 Reservas sin completar:")
            for reserva in missing[:5]:  # Mostrar solo las primeras 5
                customer = reserva.get('customer_name', 'Sin nombre')
                starts_at = reserva.get('starts_at')
                if starts_at:
                    if isinstance(starts_at, str):
                        try:
                            starts_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
                        except:
                            pass
                    if isinstance(starts_at, datetime):
                        time_str = starts_at.strftime("%H:%M")
                    else:
                        time_str = str(starts_at)
                else:
                    time_str = "N/A"
                logger.info(f"  - {time_str} - {customer}")
        
        # Enviar el reporte
        logger.info("📤 Enviando reporte...")
        await monitor._send_daily_report(
            yesterday,
            appointments_count,
            info_count,
            missing
        )
        
        logger.info("✅ Reporte de prueba enviado exitosamente!")
        logger.info("📱 Revisa WhatsApp y Email para ver el reporte completo")
        
    except Exception as e:
        logger.error(f"❌ Error en la prueba: {e}", exc_info=True)
        logger.error("💡 Verifica:")
        logger.error("   1. Que DATABASE_URL esté configurada correctamente")
        logger.error("   2. Que la base de datos esté accesible")
        logger.error("   3. Que las tablas 'booknetic_appointments' y 'Informacion Reservas' existan")
    
    # Cerrar conexiones
    await notification_manager.close()
    if hasattr(monitor, 'db') and monitor.db:
        # El monitor hereda de BaseMonitor que tiene db
        pass  # Se cierra automáticamente


if __name__ == "__main__":
    asyncio.run(test_daily_summary())

