"""
Script optimizado para calcular ingresos del mes
Usa una sola query SQL para todo el mes
"""

import sys
import asyncio
from datetime import datetime, date
from pathlib import Path

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from decimal import Decimal

async def calculate_month_to_date():
    """
    Calcula los ingresos acumulados del mes actual hasta hoy
    Usando una sola query optimizada
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
    
    # Inicializar notificaciones
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        # Cargar precios y aliases
        prices = await monitor._load_prices()
        category_aliases = monitor._get_category_aliases()
        base_prices = monitor._get_base_prices_by_people()
        
        # Query optimizada que trae todos los datos del mes de una sola vez
        query = """
            WITH payments_data AS (
                SELECT 
                    bp.id as payment_id,
                    DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as payment_date,
                    TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
                    bp.raw as payment_raw,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')),
                                     TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                        ORDER BY bp.id
                    ) as payment_row_num
                FROM booknetic_payments bp
                WHERE bp.raw->>'appointment_date' IS NOT NULL
                  AND DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) >= %s
                  AND DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) <= %s
            ),
            reservations_with_extras AS (
                SELECT 
                    ir.id as reservation_id,
                    TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                    ir.raw->>'horario_salida' as horario_salida,
                    ir.raw as extras_json,
                    ROW_NUMBER() OVER (
                        PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                     ir.raw->>'horario_salida'
                        ORDER BY ir.created_at ASC
                    ) as reservation_row_num
                FROM "Informacion Reservas" ir
                WHERE ir.raw->>'fecha' IS NOT NULL
                  AND TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') >= %s
                  AND TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') <= %s
            )
            SELECT 
                pd.payment_id,
                pd.payment_date,
                pd.appointment_datetime,
                pd.payment_raw,
                r.extras_json
            FROM payments_data pd
            LEFT JOIN reservations_with_extras r 
                ON pd.payment_date = r.reservation_date
                AND TO_CHAR(pd.appointment_datetime, 'HH24:MI:SS') = r.horario_salida
                AND pd.payment_row_num = r.reservation_row_num
            ORDER BY pd.payment_date, pd.appointment_datetime
        """
        
        print("Consultando base de datos...")
        results = await monitor.db.execute_query(
            query, 
            (month_start, today, month_start, today)
        )
        
        print(f"Procesando {len(results)} reservas...\n")
        
        # Procesar resultados
        daily_stats = {}
        total_revenue = Decimal('0')
        total_revenue_reservations = Decimal('0')
        total_revenue_extras = Decimal('0')
        total_reservations = 0
        missing_prices = set()
        
        for row in results:
            payment_date = row.get('payment_date')
            payment_raw = row.get('payment_raw', {})
            extras_json = row.get('extras_json')
            
            # Extraer número de personas
            num_people = None
            for cand in [payment_raw.get('num_people'), payment_raw.get('people'), 
                        payment_raw.get('persons'), payment_raw.get('cantidad_personas')]:
                if cand:
                    try:
                        num_people = int(str(cand).strip())
                        if num_people > 0:
                            break
                    except (ValueError, AttributeError):
                        continue
            
            # Obtener precio base
            base_price = base_prices.get(num_people, 0)
            
            # Extraer descuento
            discount_percent = 0
            for cand in [payment_raw.get('discount'), payment_raw.get('discount_percent'), 
                        payment_raw.get('descuento')]:
                if cand:
                    try:
                        discount_percent = float(str(cand).strip().replace('%', ''))
                        break
                    except (ValueError, AttributeError):
                        continue
            
            # Calcular ingreso de reserva
            reservation_total = Decimal(str(base_price * (1 - discount_percent / 100)))
            
            # Calcular extras
            extras_list = monitor._extract_extras_from_json(
                extras_json, 
                prices, 
                category_aliases,
                missing_prices
            ) if extras_json else []
            
            extras_total = sum(extra['subtotal'] for extra in extras_list)
            
            # Acumular totales
            total_revenue_reservations += reservation_total
            total_revenue_extras += Decimal(str(extras_total))
            total_revenue += reservation_total + Decimal(str(extras_total))
            total_reservations += 1
            
            # Acumular por día
            if payment_date not in daily_stats:
                daily_stats[payment_date] = {
                    'reservations': 0,
                    'revenue': Decimal('0'),
                    'revenue_res': Decimal('0'),
                    'revenue_ext': Decimal('0')
                }
            
            daily_stats[payment_date]['reservations'] += 1
            daily_stats[payment_date]['revenue'] += reservation_total + Decimal(str(extras_total))
            daily_stats[payment_date]['revenue_res'] += reservation_total
            daily_stats[payment_date]['revenue_ext'] += Decimal(str(extras_total))
        
        # Mostrar resumen
        print(f"{'='*60}")
        print(f"RESUMEN DEL MES")
        print(f"{'='*60}\n")
        
        print(f"Dias con actividad: {len(daily_stats)}")
        print(f"Total reservas: {total_reservations}")
        print(f"\nIngresos por reservas: ${float(total_revenue_reservations):,.0f}")
        print(f"Ingresos por extras: ${float(total_revenue_extras):,.0f}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"TOTAL INGRESOS: ${float(total_revenue):,.0f}")
        
        if total_reservations > 0:
            avg_per_reservation = float(total_revenue) / total_reservations
            print(f"Promedio por reserva: ${avg_per_reservation:,.0f}")
        
        if len(daily_stats) > 0:
            avg_per_day = float(total_revenue) / len(daily_stats)
            print(f"Promedio por dia: ${avg_per_day:,.0f}")
        
        # Proyección del mes
        days_elapsed = (today - month_start).days + 1
        days_in_month = 31 if today.month in [1, 3, 5, 7, 8, 10, 12] else (30 if today.month != 2 else 28)
        
        if len(daily_stats) > 0:
            daily_avg = float(total_revenue) / len(daily_stats)
            days_remaining = days_in_month - days_elapsed
            projected_month = float(total_revenue) + (daily_avg * days_remaining)
            
            print(f"\n{'='*60}")
            print(f"PROYECCION DEL MES")
            print(f"{'='*60}\n")
            print(f"Dias transcurridos: {days_elapsed}/{days_in_month}")
            print(f"Dias restantes: {days_remaining}")
            print(f"Proyeccion mes completo: ${projected_month:,.0f}")
            print(f"   (basado en promedio de ${daily_avg:,.0f}/dia)")
        
        # Top 5 días
        if daily_stats:
            print(f"\n{'='*60}")
            print(f"TOP 5 DIAS CON MAS INGRESOS")
            print(f"{'='*60}\n")
            
            sorted_days = sorted(
                daily_stats.items(), 
                key=lambda x: x[1]['revenue'], 
                reverse=True
            )[:5]
            
            for idx, (day, stats) in enumerate(sorted_days, 1):
                revenue = float(stats['revenue'])
                reservations = stats['reservations']
                
                print(f"{idx}. {day.strftime('%d/%m/%Y')}")
                print(f"   ${revenue:,.0f} ({reservations} reservas)")
        
        # Advertencias
        if missing_prices:
            print(f"\n{'='*60}")
            print(f"EXTRAS SIN PRECIO:")
            for item in list(missing_prices)[:10]:
                print(f"  - {item}")
        
        print(f"\n{'='*60}\n")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await notification_manager.close()


if __name__ == "__main__":
    asyncio.run(calculate_month_to_date())
