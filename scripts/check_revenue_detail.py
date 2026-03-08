"""Script para ver el detalle de ingresos por reserva"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

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


async def check_revenue_detail(target_date_str: str):
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Formato inválido: {target_date_str}")
        return
    
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    await asyncio.sleep(1)
    
    print(f"\n{'='*80}")
    print(f"DETALLE DE INGRESOS - {target_date.strftime('%d/%m/%Y')}")
    print(f"{'='*80}\n")
    
    revenue_data = await monitor._calculate_revenue_for_date(target_date)
    
    details = revenue_data.get('details', [])
    print(f"Total de pagos: {len(details)}\n")
    
    for idx, detail in enumerate(details, 1):
        customer = detail.get('customer_name', 'Sin nombre')
        appt_time = detail.get('appointment_datetime')
        
        if appt_time:
            if isinstance(appt_time, str):
                try:
                    appt_time = datetime.fromisoformat(appt_time.replace('Z', '+00:00'))
                except:
                    pass
            time_str = appt_time.strftime("%H:%M") if isinstance(appt_time, datetime) else str(appt_time)
        else:
            time_str = "N/A"
        
        res_total = detail.get('reservation_total', 0)
        extras_total = detail.get('extras_total', 0)
        total = detail.get('total_with_extras', 0)
        extras_list = detail.get('extras', [])
        
        print(f"{idx}. {time_str} - {customer}")
        print(f"   Reserva: ${res_total:,.0f}")
        
        if extras_list:
            print(f"   Extras (${extras_total:,.0f}):")
            for extra in extras_list:
                qty = extra.get('cantidad', 0)
                nombre = extra.get('nombre', 'Item')
                precio = extra.get('precio_unitario', 0)
                subtotal = extra.get('subtotal', 0)
                print(f"      - {qty}x {nombre} @ ${precio:,.0f} = ${subtotal:,.0f}")
        else:
            print(f"   Extras: Sin extras")
        
        print(f"   TOTAL: ${total:,.0f}")
        print()
    
    print(f"{'='*80}")
    print(f"RESUMEN:")
    print(f"  Total Reservas: ${revenue_data.get('revenue_reservations', 0):,.0f}")
    print(f"  Total Extras:   ${revenue_data.get('revenue_extras', 0):,.0f}")
    print(f"  TOTAL INGRESOS: ${revenue_data.get('total_revenue', 0):,.0f}")
    print(f"  Promedio:       ${revenue_data.get('average_revenue', 0):,.0f}")
    print(f"{'='*80}\n")
    
    await notification_manager.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/check_revenue_detail.py YYYY-MM-DD")
        sys.exit(1)
    
    asyncio.run(check_revenue_detail(sys.argv[1]))
