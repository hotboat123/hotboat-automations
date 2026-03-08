"""
Script de prueba para generar reportes bajo demanda
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Fix para Windows: psycopg requiere WindowsSelectorEventLoopPolicy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.monitors.weekly_monthly_summary_monitor import WeeklyMonthlySummaryMonitor


async def test_daily_report():
    """Genera reporte diario de ayer"""
    print("\n" + "="*80)
    print("GENERANDO REPORTE DIARIO (AYER)")
    print("="*80 + "\n")
    
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = DailySummaryMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("daily_summary", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    # Forzar generación del reporte de ayer
    yesterday = datetime.now().date() - timedelta(days=1)
    await monitor.detect_changes([{"generate_report": True, "date": yesterday}])
    
    await notification_manager.close()
    try:
        print("\n✅ Reporte diario generado\n")
    except UnicodeEncodeError:
        print("\n[OK] Reporte diario generado\n")


async def test_weekly_report():
    """Genera reporte semanal de la semana pasada"""
    print("\n" + "="*80)
    print("GENERANDO REPORTE SEMANAL (SEMANA PASADA)")
    print("="*80 + "\n")
    
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = WeeklyMonthlySummaryMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("weekly_monthly_summary", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    # Calcular el lunes de la semana pasada
    today = datetime.now().date()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    
    # Forzar generación del reporte semanal
    await monitor.detect_changes([{"type": "weekly", "date": last_monday}])
    
    await notification_manager.close()
    try:
        print("\n✅ Reporte semanal generado\n")
    except UnicodeEncodeError:
        print("\n[OK] Reporte semanal generado\n")


async def test_monthly_report():
    """Genera reporte mensual del mes pasado"""
    print("\n" + "="*80)
    print("GENERANDO REPORTE MENSUAL (MES PASADO)")
    print("="*80 + "\n")
    
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = WeeklyMonthlySummaryMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("weekly_monthly_summary", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    # Calcular el primer día del mes actual (para usar como referencia)
    today = datetime.now().date()
    first_day_current = today.replace(day=1)
    
    # Forzar generación del reporte mensual
    await monitor.detect_changes([{"type": "monthly", "date": first_day_current}])
    
    await notification_manager.close()
    try:
        print("\n✅ Reporte mensual generado\n")
    except UnicodeEncodeError:
        print("\n[OK] Reporte mensual generado\n")


async def test_all_reports():
    """Genera los 3 reportes"""
    print("\n" + "="*80)
    print("🧪 GENERANDO TODOS LOS REPORTES DE PRUEBA")
    print("="*80)
    
    try:
        await test_daily_report()
        await test_weekly_report()
        await test_monthly_report()
        
        try:
            print("\n" + "="*80)
            print("✅ TODOS LOS REPORTES GENERADOS EXITOSAMENTE")
            print("="*80)
            print("\n📧 Revisa tu email para ver los reportes\n")
        except UnicodeEncodeError:
            print("\n" + "="*80)
            print("[OK] TODOS LOS REPORTES GENERADOS EXITOSAMENTE")
            print("="*80)
            print("\n[EMAIL] Revisa tu email para ver los reportes\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Genera reportes de prueba')
    parser.add_argument('--tipo', choices=['diario', 'semanal', 'mensual', 'todos'], 
                       default='todos', help='Tipo de reporte a generar')
    
    args = parser.parse_args()
    
    if args.tipo == 'diario':
        exit_code = asyncio.run(test_daily_report())
    elif args.tipo == 'semanal':
        exit_code = asyncio.run(test_weekly_report())
    elif args.tipo == 'mensual':
        exit_code = asyncio.run(test_monthly_report())
    else:
        exit_code = asyncio.run(test_all_reports())
    
    sys.exit(exit_code or 0)
