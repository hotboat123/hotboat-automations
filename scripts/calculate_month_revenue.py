"""
Script para calcular ingresos acumulados del mes
"""

import sys
import asyncio
from datetime import datetime, date, timedelta
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager

async def calculate_month_to_date():
    """
    Calcula los ingresos acumulados del mes actual hasta hoy
    """
    
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    print(f"\n{'='*60}")
    print(f"INGRESOS DEL MES HASTA HOY")
    print(f"Periodo: {month_start.strftime('%d/%m/%Y')} - {today.strftime('%d/%m/%Y')}")
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
        total_revenue = 0
        total_revenue_reservations = 0
        total_revenue_extras = 0
        total_reservations = 0
        days_with_revenue = []
        
        # Iterar por cada día del mes hasta hoy
        current_date = month_start
        while current_date <= today:
            print(f"Calculando {current_date.strftime('%d/%m/%Y')}...", end=" ")
            
            revenue_data = await monitor._calculate_revenue_for_date(current_date)
            
            day_revenue = revenue_data.get('total_revenue', 0)
            day_reservations = revenue_data.get('total_reservations', 0)
            day_revenue_res = revenue_data.get('revenue_reservations', 0)
            day_revenue_ext = revenue_data.get('revenue_extras', 0)
            
            if day_revenue > 0:
                total_revenue += day_revenue
                total_revenue_reservations += day_revenue_res
                total_revenue_extras += day_revenue_ext
                total_reservations += day_reservations
                
                days_with_revenue.append({
                    'date': current_date,
                    'revenue': day_revenue,
                    'reservations': day_reservations,
                    'revenue_res': day_revenue_res,
                    'revenue_ext': day_revenue_ext
                })
                
                print(f"OK ${day_revenue:,.0f} ({day_reservations} reservas)")
            else:
                print("Sin actividad")
            
            current_date += timedelta(days=1)
        
        # Mostrar resumen
        print(f"\n{'='*60}")
        print(f"RESUMEN DEL MES")
        print(f"{'='*60}\n")
        
        print(f"Dias con actividad: {len(days_with_revenue)}")
        print(f"Total reservas: {total_reservations}")
        print(f"\nIngresos por reservas: ${total_revenue_reservations:,.0f}")
        print(f"Ingresos por extras: ${total_revenue_extras:,.0f}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"TOTAL INGRESOS: ${total_revenue:,.0f}")
        
        if total_reservations > 0:
            avg_per_reservation = total_revenue / total_reservations
            print(f"Promedio por reserva: ${avg_per_reservation:,.0f}")
        
        if len(days_with_revenue) > 0:
            avg_per_day = total_revenue / len(days_with_revenue)
            print(f"Promedio por dia: ${avg_per_day:,.0f}")
        
        # Proyección del mes
        days_elapsed = (today - month_start).days + 1
        days_in_month = 31 if today.month in [1, 3, 5, 7, 8, 10, 12] else (30 if today.month != 2 else 28)
        
        if len(days_with_revenue) > 0:
            daily_avg = total_revenue / len(days_with_revenue)
            days_remaining = days_in_month - days_elapsed
            projected_month = total_revenue + (daily_avg * days_remaining)
            
            print(f"\n{'='*60}")
            print(f"PROYECCION DEL MES")
            print(f"{'='*60}\n")
            print(f"Dias transcurridos: {days_elapsed}/{days_in_month}")
            print(f"Dias restantes: {days_remaining}")
            print(f"Proyeccion mes completo: ${projected_month:,.0f}")
            print(f"   (basado en promedio de ${daily_avg:,.0f}/dia)")
        
        # Top 5 días
        if days_with_revenue:
            print(f"\n{'='*60}")
            print(f"TOP 5 DIAS CON MAS INGRESOS")
            print(f"{'='*60}\n")
            
            top_days = sorted(days_with_revenue, key=lambda x: x['revenue'], reverse=True)[:5]
            for idx, day_data in enumerate(top_days, 1):
                day = day_data['date']
                revenue = day_data['revenue']
                reservations = day_data['reservations']
                
                print(f"{idx}. {day.strftime('%d/%m/%Y')}")
                print(f"   ${revenue:,.0f} ({reservations} reservas)")
        
        print(f"\n{'='*60}\n")
    
    finally:
        await notification_manager.close()


if __name__ == "__main__":
    asyncio.run(calculate_month_to_date())
