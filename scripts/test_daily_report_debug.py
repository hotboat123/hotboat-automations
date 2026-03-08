"""
Script para verificar generación de reporte diario manualmente
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.monitors.daily_summary_monitor import DailySummaryMonitor


async def test_report_generation():
    """Prueba generación de reporte con debug"""
    print("\n" + "="*80)
    print("PRUEBA DE GENERACION DE REPORTE DIARIO")
    print("="*80 + "\n")
    
    settings = get_settings()
    config = load_yaml_config()
    
    print(f"Email habilitado: {settings.email_enabled}")
    print(f"Email destino: {settings.email_to}")
    print(f"Email remitente: {settings.email_from}")
    print(f"SMTP Host: {settings.smtp_host}")
    print(f"SMTP User: {settings.smtp_username}")
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = DailySummaryMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("daily_summary", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    # Fecha de ayer
    yesterday = datetime.now().date() - timedelta(days=1)
    print(f"\nGenerando reporte para: {yesterday}")
    
    # Obtener datos
    try:
        summary_data = await monitor._get_daily_summary(yesterday)
        print(f"\nDatos del resumen:")
        print(f"  - Total reservas: {summary_data.get('total_reservas', 0)}")
        print(f"  - Con info: {summary_data.get('reservas_con_info', 0)}")
        print(f"  - Sin info: {summary_data.get('reservas_sin_info', 0)}")
        print(f"  - Total ingresos: ${summary_data.get('total_ingresos', 0):,.0f}")
        print(f"  - Total costos: ${summary_data.get('total_costos_operativos', 0):,.0f}")
        
        # Obtener costo de marketing
        marketing_cost = await monitor._get_marketing_cost(yesterday)
        print(f"  - Costo marketing: ${marketing_cost:,.0f}")
        
        # Intentar enviar reporte
        print(f"\nIntentando enviar reporte...")
        await monitor._send_daily_report(yesterday, summary_data, marketing_cost)
        print(f"[OK] Reporte enviado exitosamente!")
        
    except Exception as e:
        print(f"[ERROR] Error generando reporte: {e}")
        import traceback
        traceback.print_exc()
    
    await notification_manager.close()
    print("\n[OK] Prueba completada\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_report_generation())
    except UnicodeEncodeError as e:
        print("\n[OK] Prueba completada (error de encoding en consola Windows)")
