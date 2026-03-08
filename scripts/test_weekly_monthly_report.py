"""
Script para probar el reporte semanal/mensual
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
from app.monitors.weekly_monthly_summary_monitor import WeeklyMonthlySummaryMonitor
from app.notifications.manager import NotificationManager


async def test_report(report_type: str, use_current: bool = False):
    """Prueba el reporte semanal o mensual
    
    Args:
        report_type: 'weekly' o 'monthly'
        use_current: Si es True, usa el período actual en progreso en vez del último completo
    """
    
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("weekly_monthly_summary", {})
    monitor = WeeklyMonthlySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    # Esperar un poco
    await asyncio.sleep(2)
    
    # Determinar fechas según el tipo de reporte
    if report_type == "weekly":
        today = datetime.now().date()
        days_since_monday = today.weekday()
        
        if use_current:
            # Semana actual en progreso (desde el lunes hasta hoy)
            current_monday = today - timedelta(days=days_since_monday)
            start_date = current_monday
            end_date = today
            period_name = "SEMANA ACTUAL (en progreso)"
        else:
            # Última semana completa (lunes a domingo anterior)
            last_sunday = today - timedelta(days=days_since_monday + 1)
            last_monday = last_sunday - timedelta(days=6)
            start_date = last_monday
            end_date = last_sunday
            period_name = "ÚLTIMA SEMANA COMPLETA"
        
        logger.info(f"📅 Generando reporte semanal - {period_name}")
        logger.info(f"   Desde: {start_date.strftime('%d/%m/%Y')}")
        logger.info(f"   Hasta: {end_date.strftime('%d/%m/%Y')}")
        
        report_config = [{
            "type": "weekly",
            "start_date": start_date,
            "end_date": end_date
        }]
        
    else:  # monthly
        today = datetime.now().date()
        
        if use_current:
            # Mes actual en progreso (desde el día 1 hasta hoy)
            first_day_current_month = today.replace(day=1)
            start_date = first_day_current_month
            end_date = today
            period_name = "MES ACTUAL (en progreso)"
        else:
            # Mes anterior completo
            first_day_current_month = today.replace(day=1)
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            first_day_previous_month = last_day_previous_month.replace(day=1)
            start_date = first_day_previous_month
            end_date = last_day_previous_month
            period_name = "MES ANTERIOR COMPLETO"
        
        logger.info(f"📅 Generando reporte mensual - {period_name}")
        logger.info(f"   Desde: {start_date.strftime('%d/%m/%Y')}")
        logger.info(f"   Hasta: {end_date.strftime('%d/%m/%Y')}")
        
        report_config = [{
            "type": "monthly",
            "start_date": start_date,
            "end_date": end_date
        }]
    
    # Generar y enviar reporte
    try:
        await monitor.detect_changes(report_config)
        logger.info("✅ Reporte enviado! Revisa tu Email")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    
    await notification_manager.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_weekly_monthly_report.py [weekly|monthly] [current]")
        print("")
        print("Argumentos:")
        print("  weekly   - Reporte semanal")
        print("  monthly  - Reporte mensual")
        print("  current  - (Opcional) Usar período actual en progreso")
        print("")
        print("Ejemplos:")
        print("  python scripts/test_weekly_monthly_report.py weekly")
        print("    → Última semana completa (lunes a domingo anterior)")
        print("")
        print("  python scripts/test_weekly_monthly_report.py weekly current")
        print("    → Semana actual en progreso (desde el lunes hasta hoy)")
        print("")
        print("  python scripts/test_weekly_monthly_report.py monthly current")
        print("    → Mes actual en progreso (desde el día 1 hasta hoy)")
        sys.exit(1)
    
    report_type = sys.argv[1].lower()
    use_current = len(sys.argv) > 2 and sys.argv[2].lower() == "current"
    
    if report_type not in ["weekly", "monthly"]:
        print("Error: tipo de reporte debe ser 'weekly' o 'monthly'")
        sys.exit(1)
    
    asyncio.run(test_report(report_type, use_current))
