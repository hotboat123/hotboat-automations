"""
Script simple para generar y enviar reporte diario de una fecha específica
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.monitors.daily_summary_monitor import DailySummaryMonitor


async def send_report_for_date(target_date: date):
    """Genera y envía el reporte para una fecha específica"""
    
    print(f"\nGenerando reporte para: {target_date.strftime('%d/%m/%Y')}")
    print("="*80)
    
    # Cargar configuración
    settings = get_settings()
    config = load_yaml_config()
    
    # Debug: Verificar configuración de email
    print("\nVerificando configuración de email:")
    import os
    print(f"  EMAIL_TO: {os.getenv('EMAIL_TO')}")
    print(f"  EMAIL_FROM: {os.getenv('EMAIL_FROM')}")
    print(f"  SMTP_HOST: {os.getenv('SMTP_HOST')}")
    print(f"  SMTP_USERNAME: {os.getenv('SMTP_USERNAME')}")
    print(f"  SMTP_PASSWORD: {'SET' if os.getenv('SMTP_PASSWORD') else 'NOT SET'}")
    print(f"  Email enabled in config: {config['notifications']['email']['enabled']}")
    print()
    
    # Inicializar notification manager
    notification_manager = NotificationManager(settings, config)
    
    try:
        await notification_manager.initialize()
        print(f"Notificadores inicializados: {list(notification_manager.notifiers.keys())}")
    except Exception as e:
        print(f"Error inicializando notification manager: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Inicializar monitor de resumen diario
    monitor_config = config["monitors"]["daily_summary"]
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        # Obtener datos del día
        print(f"\nObteniendo datos de {target_date.strftime('%d/%m/%Y')}...")
        summary_data = await monitor._get_daily_summary(target_date)
        
        print(f"Total reservas: {summary_data['total_reservas']}")
        print(f"  - Con info: {summary_data['reservas_con_info']}")
        print(f"  - Sin info: {summary_data['reservas_sin_info']}")
        print(f"Total ingresos: ${summary_data['total_ingresos']:,.0f}")
        
        # Obtener costos de marketing
        marketing_cost = await monitor._get_marketing_cost(target_date)
        print(f"Marketing: ${marketing_cost['total_marketing']:,.0f}")
        
        # Enviar reporte
        print("\nEnviando reporte por email...")
        await monitor._send_daily_report(target_date, summary_data, marketing_cost)
        
        print("\nReporte enviado exitosamente!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await notification_manager.close()
        print("\n" + "="*80)
        print("PROCESO COMPLETADO")
        print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/send_daily_report.py YYYY-MM-DD")
        print("Ejemplo: python scripts/send_daily_report.py 2026-03-10")
        sys.exit(1)
    
    date_arg = sys.argv[1]
    try:
        target_date = datetime.strptime(date_arg, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Formato de fecha inválido. Use YYYY-MM-DD")
        sys.exit(1)
    
    asyncio.run(send_report_for_date(target_date))
