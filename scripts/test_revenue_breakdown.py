"""
Script para probar el desglose detallado de ingresos
Muestra en consola el cálculo paso a paso
"""

import sys
import asyncio
from datetime import datetime, date
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager

async def test_revenue(date_str: str):
    """
    Prueba el cálculo de ingresos para una fecha específica
    """
    
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    print(f"\n{'='*60}")
    print(f"Desglose de Ingresos para {target_date.strftime('%d/%m/%Y')}")
    print(f"{'='*60}\n")
    
    # Cargar configuración
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones (requerido por el monitor)
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        # Calcular ingresos
        revenue_data = await monitor._calculate_revenue_for_date(target_date)
        
        print(f"RESUMEN GENERAL")
        print(f"{'-'*60}")
        print(f"Total Reservas: {revenue_data['total_reservations']}")
        print(f"Ingresos Reservas: ${revenue_data['revenue_reservations']:,.0f}")
        print(f"Ingresos Extras: ${revenue_data['revenue_extras']:,.0f}")
        print(f"TOTAL: ${revenue_data['total_revenue']:,.0f}")
        print(f"Promedio por reserva: ${revenue_data['average_revenue']:,.0f}\n")
        
        # Mostrar cada reserva
        details = revenue_data.get('details', [])
        
        if details:
            print(f"\nDETALLE POR RESERVA:")
            print(f"{'-'*60}\n")
            
            for idx, detail in enumerate(details, 1):
                customer = detail.get('customer_name', 'Sin nombre')
                num_people = detail.get('num_people', 0)
                base_price = detail.get('base_price', 0)
                discount = detail.get('discount_percent', 0)
                res_total = detail.get('reservation_total', 0)
                extras_total = detail.get('extras_total', 0)
                total = detail.get('total_with_extras', 0)
                
                appt_time = detail.get('appointment_datetime')
                if appt_time:
                    time_str = appt_time.strftime("%H:%M")
                else:
                    time_str = "N/A"
                
                print(f"Reserva #{idx} - {time_str}")
                print(f"  Cliente: {customer}")
                
                if num_people and base_price:
                    print(f"  👥 {num_people} personas")
                    print(f"  💵 Precio base: ${base_price:,.0f}")
                    if discount > 0:
                        print(f"  🏷️  Descuento: {discount:.0f}%")
                        print(f"      (${base_price * discount / 100:,.0f})")
                    print(f"  ➡️  Subtotal Reserva: ${res_total:,.0f}")
                else:
                    print(f"  ⚠️  No se pudo determinar personas/precio base")
                    print(f"  💵 Subtotal Reserva: ${res_total:,.0f}")
                
                extras_list = detail.get('extras', [])
                if extras_list:
                    print(f"  🍾 Extras:")
                    for extra in extras_list[:5]:  # Mostrar hasta 5
                        qty = extra.get('cantidad', 0)
                        nombre = extra.get('nombre', 'Item')
                        precio = extra.get('precio_unitario', 0)
                        subtotal = extra.get('subtotal', 0)
                        print(f"     • {qty}x {nombre} @ ${precio:,.0f} = ${subtotal:,.0f}")
                    
                    if len(extras_list) > 5:
                        print(f"     ... y {len(extras_list) - 5} extras más")
                    
                    print(f"  ➡️  Total Extras: ${extras_total:,.0f}")
                
                print(f"  💰 TOTAL: ${total:,.0f}")
                print()
        
        # Advertencias
        missing = revenue_data.get('missing_prices', [])
        if missing:
            print(f"\n⚠️  EXTRAS SIN PRECIO:")
            for item in missing[:10]:
                print(f"  • {item}")
            if len(missing) > 10:
                print(f"  ... y {len(missing) - 10} más")
    
    finally:
        await notification_manager.close()
        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_revenue_breakdown.py YYYY-MM-DD")
        sys.exit(1)
    
    date_arg = sys.argv[1]
    asyncio.run(test_revenue(date_arg))
