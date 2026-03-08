"""
Script para exportar ingresos del mes a CSV
"""

import sys
import asyncio
import csv
from datetime import datetime, date
from pathlib import Path
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

async def export_month_to_csv(month: int = None, year: int = None):
    """
    Exporta los ingresos del mes a un archivo CSV
    """
    
    today = date.today()
    
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    # Calcular el rango del mes
    month_start = date(year, month, 1)
    
    # Si es el mes actual, hasta hoy; si no, hasta el último día del mes
    if year == today.year and month == today.month:
        month_end = today
    else:
        # Último día del mes
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            from datetime import timedelta
            month_end = date(year, month + 1, 1) - timedelta(days=1)
    
    print(f"\n{'='*60}")
    print(f"EXPORTANDO INGRESOS A CSV")
    print(f"Periodo: {month_start.strftime('%d/%m/%Y')} - {month_end.strftime('%d/%m/%Y')}")
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
        
        # Query optimizada
        query = """
            WITH payments_data AS (
                SELECT 
                    bp.id as payment_id,
                    DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as payment_date,
                    TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
                    bp.raw->>'customer' as customer_name,
                    bp.raw->>'customer_email' as customer_email,
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
                pd.customer_name,
                pd.customer_email,
                pd.service_name,
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
            (month_start, month_end, month_start, month_end)
        )
        
        print(f"Procesando {len(results)} reservas...\n")
        
        # Preparar datos para CSV
        csv_data = []
        missing_prices = set()
        
        for row in results:
            payment_date = row.get('payment_date')
            appointment_datetime = row.get('appointment_datetime')
            customer_name = row.get('customer_name', 'Sin nombre')
            customer_email = row.get('customer_email', '')
            service_name = row.get('service_name', '')
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
            
            # Si no se encontró, intentar extraer del servicio
            if not num_people and service_name:
                import re
                match = re.search(r'(\d+)\s*(?:personas|people|pax)', str(service_name), re.IGNORECASE)
                if match:
                    num_people = int(match.group(1))
            
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
            reservation_total = float(Decimal(str(base_price * (1 - discount_percent / 100))))
            
            # Calcular extras
            extras_list = monitor._extract_extras_from_json(
                extras_json, 
                prices, 
                category_aliases,
                missing_prices
            ) if extras_json else []
            
            extras_total = sum(extra['subtotal'] for extra in extras_list)
            
            # Crear desglose de extras
            extras_detail = '; '.join([
                f"{extra['cantidad']}x {extra['nombre']} (${extra['subtotal']:,.0f})"
                for extra in extras_list
            ]) if extras_list else 'Sin extras'
            
            # Agregar fila al CSV
            csv_data.append({
                'fecha': payment_date.strftime('%d/%m/%Y') if payment_date else '',
                'hora': appointment_datetime.strftime('%H:%M') if appointment_datetime else '',
                'cliente': customer_name,
                'email': customer_email,
                'servicio': service_name,
                'num_personas': num_people if num_people else '',
                'precio_base': base_price if base_price else 0,
                'descuento_%': discount_percent if discount_percent else 0,
                'precio_reserva': reservation_total,
                'extras_detalle': extras_detail,
                'precio_extras': extras_total,
                'precio_total': reservation_total + extras_total
            })
        
        # Generar nombre de archivo
        filename = f"ingresos_{year}-{month:02d}.csv"
        
        # Crear carpeta exports si no existe
        exports_dir = Path('exports')
        exports_dir.mkdir(exist_ok=True)
        
        filepath = exports_dir / filename
        
        # Escribir CSV
        print(f"Generando archivo {filename}...")
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'fecha', 'hora', 'cliente', 'email', 'servicio',
                'num_personas', 'precio_base', 'descuento_%',
                'precio_reserva', 'extras_detalle', 'precio_extras', 'precio_total'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        # Calcular totales
        total_revenue_reservations = sum(row['precio_reserva'] for row in csv_data)
        total_revenue_extras = sum(row['precio_extras'] for row in csv_data)
        total_revenue = total_revenue_reservations + total_revenue_extras
        
        print(f"\n{'='*60}")
        print(f"ARCHIVO GENERADO EXITOSAMENTE")
        print(f"{'='*60}\n")
        print(f"Ubicacion: {filepath.absolute()}")
        print(f"Total registros: {len(csv_data)}")
        print(f"\nRESUMEN:")
        print(f"  Ingresos por reservas: ${total_revenue_reservations:,.0f}")
        print(f"  Ingresos por extras:   ${total_revenue_extras:,.0f}")
        print(f"  TOTAL INGRESOS:        ${total_revenue:,.0f}")
        
        if len(csv_data) > 0:
            print(f"  Promedio por reserva:  ${total_revenue / len(csv_data):,.0f}")
        
        if missing_prices:
            print(f"\nADVERTENCIA - Extras sin precio:")
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
    # Permitir especificar mes y año
    month = None
    year = None
    
    if len(sys.argv) >= 2:
        month = int(sys.argv[1])
    if len(sys.argv) >= 3:
        year = int(sys.argv[2])
    
    asyncio.run(export_month_to_csv(month, year))
