"""
Script para analizar estructura de ingresos y proponer sistema de comisiones
"""

import sys
import asyncio
import csv
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager

async def analyze_revenue_structure(month: int = None, year: int = None):
    """
    Analiza la estructura de ingresos para diseñar sistema de comisiones
    """
    
    today = date.today()
    
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    month_start = date(year, month, 1)
    month_end = today if (year == today.year and month == today.month) else date(year, month + 1, 1)
    
    print(f"\n{'='*70}")
    print(f"ANALISIS DE ESTRUCTURA DE INGRESOS")
    print(f"Periodo: {month_start.strftime('%d/%m/%Y')} - {month_end.strftime('%d/%m/%Y')}")
    print(f"{'='*70}\n")
    
    # Cargar configuración
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        prices = await monitor._load_prices()
        category_aliases = monitor._get_category_aliases()
        base_prices = monitor._get_base_prices_by_people()
        
        # Query
        query = """
            WITH payments_data AS (
                SELECT 
                    bp.id as payment_id,
                    DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as payment_date,
                    TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
                    bp.raw->>'customer' as customer_name,
                    bp.raw->>'service' as service_name,
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
                pd.customer_name,
                pd.service_name,
                pd.payment_raw,
                r.extras_json
            FROM payments_data pd
            LEFT JOIN reservations_with_extras r 
                ON pd.payment_date = r.reservation_date
                AND TO_CHAR(pd.appointment_datetime, 'HH24:MI:SS') = r.horario_salida
                AND pd.payment_row_num = r.reservation_row_num
            ORDER BY pd.payment_date, pd.payment_id
        """
        
        results = await monitor.db.execute_query(query, (month_start, month_end, month_start, month_end))
        
        # Estadísticas
        total_reservations = len(results)
        reservations_with_extras = 0
        reservations_without_extras = 0
        
        total_revenue_reservations = Decimal('0')
        total_revenue_extras = Decimal('0')
        
        extras_breakdown = defaultdict(lambda: {'count': 0, 'revenue': 0})
        people_distribution = defaultdict(int)
        
        missing_prices = set()
        
        for row in results:
            payment_raw = row.get('payment_raw', {})
            
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
            
            if not num_people and payment_raw.get('service'):
                import re
                match = re.search(r'(\d+)\s*(?:personas|people|pax)', str(payment_raw.get('service')), re.IGNORECASE)
                if match:
                    num_people = int(match.group(1))
            
            if num_people:
                people_distribution[num_people] += 1
            
            # Calcular ingreso de reserva
            base_price = base_prices.get(num_people, 0)
            discount_percent = 0
            for cand in [payment_raw.get('discount'), payment_raw.get('discount_percent'), 
                        payment_raw.get('descuento')]:
                if cand:
                    try:
                        discount_percent = float(str(cand).strip().replace('%', ''))
                        break
                    except (ValueError, AttributeError):
                        continue
            
            reservation_total = Decimal(str(base_price * (1 - discount_percent / 100)))
            total_revenue_reservations += reservation_total
            
            # Calcular extras
            extras_json = row.get('extras_json')
            extras_list = monitor._extract_extras_from_json(
                extras_json, prices, category_aliases, missing_prices
            ) if extras_json else []
            
            if extras_list:
                reservations_with_extras += 1
                for extra in extras_list:
                    nombre = extra.get('nombre', 'desconocido')
                    cantidad = extra.get('cantidad', 0)
                    subtotal = extra.get('subtotal', 0)
                    
                    extras_breakdown[nombre]['count'] += cantidad
                    extras_breakdown[nombre]['revenue'] += subtotal
            else:
                reservations_without_extras += 1
            
            extras_total = sum(extra['subtotal'] for extra in extras_list)
            total_revenue_extras += Decimal(str(extras_total))
        
        total_revenue = total_revenue_reservations + total_revenue_extras
        
        # Mostrar análisis
        print(f"RESUMEN GENERAL:")
        print(f"{'-'*70}")
        print(f"Total reservas: {total_reservations}")
        print(f"Reservas CON extras: {reservations_with_extras} ({reservations_with_extras/total_reservations*100:.1f}%)")
        print(f"Reservas SIN extras: {reservations_without_extras} ({reservations_without_extras/total_reservations*100:.1f}%)")
        print(f"\nIngresos por reservas: ${float(total_revenue_reservations):,.0f} ({float(total_revenue_reservations)/float(total_revenue)*100:.1f}%)")
        print(f"Ingresos por extras: ${float(total_revenue_extras):,.0f} ({float(total_revenue_extras)/float(total_revenue)*100:.1f}%)")
        print(f"TOTAL: ${float(total_revenue):,.0f}\n")
        
        print(f"\nDISTRIBUCION POR NUMERO DE PERSONAS:")
        print(f"{'-'*70}")
        for people, count in sorted(people_distribution.items()):
            print(f"{people} personas: {count} reservas ({count/total_reservations*100:.1f}%)")
        
        print(f"\n\nEXTRAS MAS VENDIDOS:")
        print(f"{'-'*70}")
        print(f"{'EXTRA':<40} {'CANTIDAD':>10} {'INGRESOS':>15}")
        print(f"{'-'*70}")
        
        sorted_extras = sorted(extras_breakdown.items(), key=lambda x: x[1]['revenue'], reverse=True)
        for extra_name, data in sorted_extras[:15]:
            count = data['count']
            revenue = data['revenue']
            print(f"{extra_name:<40} {count:>10} ${revenue:>14,.0f}")
        
        # Propuesta de sistema de comisiones
        print(f"\n\n{'='*70}")
        print(f"PROPUESTA DE SISTEMA DE COMISIONES")
        print(f"{'='*70}\n")
        
        # Calcular promedios
        avg_revenue_per_reservation = float(total_revenue) / total_reservations
        avg_extras_per_reservation = float(total_revenue_extras) / total_reservations
        
        print(f"MODELO 1: COMISION POR RESERVA + BONOS POR EXTRAS")
        print(f"{'-'*70}")
        print(f"Pago base por reserva: $15,000 - $20,000")
        print(f"+ Bono por extras vendidos: 10-15% del valor de extras")
        print(f"\nEjemplo con datos actuales:")
        print(f"  - Reserva sin extras: $15,000")
        print(f"  - Reserva con tabla ($25,000): $15,000 + $2,500 = $17,500")
        print(f"  - Reserva con tabla + marco + video ($80,000): $15,000 + $8,000 = $23,000")
        print(f"\nIngreso promedio por trabajador por reserva: ${15000 + avg_extras_per_reservation * 0.10:,.0f}")
        
        print(f"\n\nMODELO 2: COMISION VARIABLE POR MONTO TOTAL")
        print(f"{'-'*70}")
        print(f"Escalera de comisiones sobre el total:")
        print(f"  - Reservas sin extras: 8% (${avg_revenue_per_reservation * 0.08:,.0f})")
        print(f"  - Reservas con extras: 10% (${avg_revenue_per_reservation * 1.2 * 0.10:,.0f} aprox)")
        print(f"  - Bonus adicional si venden >$500k/mes: +2%")
        
        print(f"\n\nMODELO 3: HIBRIDO (RECOMENDADO)")
        print(f"{'-'*70}")
        print(f"Sueldo base mensual: $400,000 - $500,000")
        print(f"+ Comision por reserva: $5,000 fijo")
        print(f"+ Comision por extras: 15% del valor")
        print(f"+ Bonus por cumplimiento de metas:")
        print(f"  - >60% de reservas con extras: +$50,000/mes")
        print(f"  - >80% de reservas con extras: +$100,000/mes")
        print(f"  - Promedio de extras >$30k/reserva: +$75,000/mes")
        print(f"\nCon datos actuales ({reservations_with_extras/total_reservations*100:.0f}% con extras):")
        print(f"  Ingreso mensual estimado: ${500000 + (total_reservations * 5000) + (float(total_revenue_extras) * 0.15):,.0f}")
        print(f"  Costo por reserva para ti: ${(500000 + (total_reservations * 5000) + (float(total_revenue_extras) * 0.15))/total_reservations:,.0f}")
        print(f"  % sobre ingresos totales: {((500000 + (total_reservations * 5000) + (float(total_revenue_extras) * 0.15))/float(total_revenue)*100):.1f}%")
        
        print(f"\n\n{'='*70}")
        print(f"ANALISIS DE INCENTIVOS")
        print(f"{'='*70}\n")
        
        print("Actualmente:")
        print(f"  - Solo {reservations_with_extras/total_reservations*100:.0f}% de reservas tienen extras")
        print(f"  - Potencial de crecimiento: {100 - reservations_with_extras/total_reservations*100:.0f}%")
        print(f"  - Si subieras a 80% con extras: +${float(total_revenue_extras) * (0.8/(reservations_with_extras/total_reservations) - 1):,.0f}")
        
        print(f"\n\nEXTRAS CON MAYOR POTENCIAL:")
        print(f"{'-'*70}")
        print(f"1. TABLAS: Solo en {extras_breakdown.get('tabla_2_personas', {}).get('count', 0) + extras_breakdown.get('tabla_1', {}).get('count', 0)} reservas")
        print(f"   Potencial: Vender en 60% = +${(total_reservations * 0.6 - (extras_breakdown.get('tabla_2_personas', {}).get('count', 0) + extras_breakdown.get('tabla_1', {}).get('count', 0))) * 22500:,.0f}")
        
        print(f"\n2. FOTOS CON MARCO: Solo en {extras_breakdown.get('foto_con_marco', {}).get('count', 0)} reservas")
        print(f"   Potencial: Vender en 40% = +${(total_reservations * 0.4 - extras_breakdown.get('foto_con_marco', {}).get('count', 0)) * 15000:,.0f}")
        
        print(f"\n3. VIDEOS: Solo en {extras_breakdown.get('video_15_seg', {}).get('count', 0) + extras_breakdown.get('video_1_min', {}).get('count', 0)} reservas")
        print(f"   Potencial: Vender en 30% = +${(total_reservations * 0.3 - (extras_breakdown.get('video_15_seg', {}).get('count', 0) + extras_breakdown.get('video_1_min', {}).get('count', 0))) * 35000:,.0f}")
        
        print(f"\n\n{'='*70}\n")
    
    finally:
        await notification_manager.close()


if __name__ == "__main__":
    month = None
    year = None
    
    if len(sys.argv) >= 2:
        month = int(sys.argv[1])
    if len(sys.argv) >= 3:
        year = int(sys.argv[2])
    
    asyncio.run(analyze_revenue_structure(month, year))
