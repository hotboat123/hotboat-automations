"""
Script para exportar análisis diario de reservas a CSV
Genera un archivo CSV con información detallada de cada reserva
"""
import sys
import csv
import psycopg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings

def normalize_text(text: str) -> str:
    """Normaliza texto para comparación"""
    if not text:
        return ""
    
    text = str(text).lower().strip()
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    text = ''.join(c if c.isalnum() or c.isspace() else '_' for c in text)
    text = '_'.join(text.split())
    
    return text

def find_cost_for_extra(extra_name: str, costs_dict: Dict[str, float]) -> float:
    """
    Busca el costo de un extra, intentando varios métodos de matching
    """
    extra_normalized = normalize_text(extra_name)
    
    # 1. Matching exacto
    if extra_normalized in costs_dict:
        return costs_dict[extra_normalized]
    
    # 2. Mapeo específico para casos conocidos
    mappings = {
        'tabla_2_personas': 'tabla_2',
        'tabla_4_personas': 'tabla_1',
        'tabla_1_persona': 'tabla_1',
        'video_15_segundos': 'video_15_seg',
        'video_60_segundos': 'video_1_min',
        'video_1_minuto': 'video_1_min',
        'jugo_naranja': 'jugo_1l',
        'jugo_1_l': 'jugo_1l',
        'jugo_berries': 'jugo_1l',
        'jugo_natural_1lt': 'jugo_1l',
        'foto_con_marco': 'foto_con_marco',
    }
    
    if extra_normalized in mappings:
        mapped_name = mappings[extra_normalized]
        if mapped_name in costs_dict:
            return costs_dict[mapped_name]
    
    # 3. Búsqueda por palabras clave
    words = [w for w in extra_normalized.split('_') if len(w) > 2]
    
    # Buscar matches parciales
    best_match = None
    best_score = 0
    
    for bd_name, bd_cost in costs_dict.items():
        if bd_cost == 0:
            continue
        
        score = sum(1 for word in words if word in bd_name)
        if score > best_score:
            best_score = score
            best_match = bd_cost
    
    if best_score >= 1:  # Al menos una palabra coincide
        return best_match
    
    return 0

def load_costs_and_prices_from_db(conn) -> tuple[Dict[str, float], Dict[str, float]]:
    """Carga los costos Y precios desde la tabla Precios Extras"""
    costs = {}
    prices = {}
    
    with conn.cursor() as cur:
        cur.execute('SELECT raw FROM "Precios Extras"')
        
        for row in cur.fetchall():
            raw = row[0]
            if not raw:
                continue
            
            extra_name = raw.get('Extra', '')
            costo_str = raw.get('costo', '0')
            precio_str = raw.get('Precio', '0')
            
            if not extra_name:
                continue
            
            # Limpiar costo
            try:
                costo = float(str(costo_str).replace('.', '').replace(',', '').strip()) if costo_str else 0
            except (ValueError, AttributeError):
                costo = 0
            
            # Limpiar precio
            try:
                precio = float(str(precio_str).replace('.', '').replace(',', '').strip()) if precio_str else 0
            except (ValueError, AttributeError):
                precio = 0
            
            # Normalizar nombre
            normalized = normalize_text(extra_name)
            costs[normalized] = costo
            prices[normalized] = precio
    
    return costs, prices

def get_reservations_data(conn, start_date: str, end_date: str, costs_dict: Dict[str, float], prices_dict: Dict[str, float], marketing_costs_by_date: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Obtiene los datos de reservas para el rango de fechas especificado
    """
    # Costos fijos por reserva
    COSTO_GAS = 15000
    COSTO_LEÑA = 1000
    COSTO_AGUA = 1000
    COSTO_HIELO = 1000
    COSTO_FIJO_POR_RESERVA = COSTO_GAS + COSTO_LEÑA + COSTO_AGUA + COSTO_HIELO
    
    query = """
        WITH appointments_data AS (
            SELECT 
                ba.id as appointment_id,
                DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
                TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
                ba.raw->>'customer' as customer_name,
                CAST(
                    REGEXP_REPLACE(
                        REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                        '[^0-9]',
                        '',
                        'g'
                    ) AS NUMERIC
                ) as payment_amount,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                 TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                    ORDER BY ba.id
                ) as ba_row_num
            FROM booknetic_appointments ba
            WHERE (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
                AND DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) BETWEEN %s AND %s
        ),
        reservations_with_extras AS (
            SELECT 
                ir.id as reservation_id,
                TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                -- Normalizar hora a formato HH24:MI:SS
                TO_CHAR(
                    TO_TIMESTAMP(ir.raw->>'horario_salida', 'HH24:MI:SS'),
                    'HH24:MI:SS'
                ) as horario_salida,
                ir.raw as extras_json,
                ROW_NUMBER() OVER (
                    PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                 TO_CHAR(TO_TIMESTAMP(ir.raw->>'horario_salida', 'HH24:MI:SS'), 'HH24:MI:SS')
                    ORDER BY ir.created_at ASC
                ) as ir_row_num
            FROM "Informacion Reservas" ir
            WHERE ir.raw->>'fecha' IS NOT NULL
        )
        SELECT 
            ad.appointment_date as fecha,
            ad.appointment_id,
            ad.customer_name,
            ad.payment_amount,
            r.extras_json as info_raw
        FROM appointments_data ad
        LEFT JOIN reservations_with_extras r 
            ON ad.appointment_date = r.reservation_date
            AND ad.appointment_time = r.horario_salida
            AND ad.ba_row_num = r.ir_row_num
        ORDER BY ad.appointment_date, ad.appointment_id
    """
    
    results = []
    
    with conn.cursor() as cur:
        cur.execute(query, (start_date, end_date))
        
        for row in cur.fetchall():
            fecha = row[0]  # fecha
            appointment_id = row[1] if row[1] else ''  # appointment_id
            customer_name = row[2] if row[2] else 'Sin nombre'  # customer_name
            payment_amount = float(row[3]) if row[3] else 0  # payment_amount
            info_raw = row[4] if row[4] else {}  # info_raw
            
            # Procesar extras usando la misma lógica que el monitor
            extras_list = []
            ingreso_extras = 0
            costo_extras_total = 0
            
            if info_raw:
                # Procesar campos individuales de extras
                extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
                
                for key, value in info_raw.items():
                    key_lower = key.lower()
                    is_extra = any(key_lower.startswith(prefix) for prefix in extra_prefixes)
                    
                    if not is_extra:
                        continue
                    
                    # Obtener cantidad
                    try:
                        cantidad = int(str(value).strip()) if value and str(value).strip() else 0
                    except (ValueError, AttributeError):
                        cantidad = 0
                    
                    if cantidad <= 0:
                        continue
                    
                    # Extraer nombre del extra (entre corchetes)
                    import re
                    alias_match = re.search(r'\[(.+?)\]', key)
                    if alias_match:
                        extra_name = alias_match.group(1)
                    else:
                        extra_name = key
                    
                    # Buscar precio de venta usando el método inteligente
                    precio_unitario = find_cost_for_extra(extra_name, prices_dict)
                    subtotal = cantidad * precio_unitario
                    ingreso_extras += subtotal
                    
                    # Buscar costo usando el método inteligente
                    costo_unitario = find_cost_for_extra(extra_name, costs_dict)
                    costo_total_extra = cantidad * costo_unitario
                    costo_extras_total += costo_total_extra
                    
                    # Agregar a lista de extras
                    if cantidad > 0:
                        extras_list.append(f"{extra_name} x{cantidad}")
            
            # Calcular costo operativo (fijos + variables)
            costo_operativo = COSTO_FIJO_POR_RESERVA + costo_extras_total
            
            # Obtener costo de marketing para esta fecha
            costo_marketing = marketing_costs_by_date.get(fecha, 0)
            
            # Formatear extras
            extras_str = ", ".join(extras_list) if extras_list else "Sin extras"
            
            results.append({
                'Dia': fecha.strftime('%d/%m/%Y') if fecha else '',
                'Id Reserva': appointment_id[:8] if appointment_id else '',
                'Ingreso Reserva': int(payment_amount),
                'Ingreso extras': int(ingreso_extras),
                'Costo Operativo': int(costo_operativo),
                'Costo Marketing': int(costo_marketing),
                'Costo Remuneracion': 0,  # Siempre en 0 como solicitó el usuario
                'Costos Extras': int(costo_extras_total),
                'Extras': extras_str,
                'Nombre Cliente': customer_name
            })
    
    return results

def generate_daily_summary(reservations_data: List[Dict[str, Any]], marketing_costs_by_date: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Genera un resumen agregado por día
    """
    daily_summary = {}
    
    for reserva in reservations_data:
        dia = reserva.get('Dia')
        
        if dia not in daily_summary:
            daily_summary[dia] = {
                'Ingreso Reservas': 0,
                'Ingreso extras': 0,
                'Costo Operativo': 0,
                'Costo marketing': 0,
                'Costo Remuneracion': 0,
                'Costos Extras': 0,
                'extras_list': []
            }
        
        daily_summary[dia]['Ingreso Reservas'] += reserva.get('Ingreso Reserva', 0)
        daily_summary[dia]['Ingreso extras'] += reserva.get('Ingreso extras', 0)
        daily_summary[dia]['Costo Operativo'] += reserva.get('Costo Operativo', 0)
        daily_summary[dia]['Costo Remuneracion'] += reserva.get('Costo Remuneracion', 0)
        daily_summary[dia]['Costos Extras'] += reserva.get('Costos Extras', 0)
        
        # Agregar extras a la lista
        extras_str = reserva.get('Extras', '')
        if extras_str and extras_str != 'Sin extras':
            daily_summary[dia]['extras_list'].append(extras_str)
    
    # Agregar costos de marketing por día
    for dia in daily_summary:
        # Convertir dia de DD/MM/YYYY a fecha para buscar marketing
        try:
            from datetime import datetime
            fecha_obj = datetime.strptime(dia, '%d/%m/%Y').date()
            daily_summary[dia]['Costo marketing'] = marketing_costs_by_date.get(fecha_obj, 0)
        except:
            daily_summary[dia]['Costo marketing'] = 0
    
    # Convertir a lista ordenada por fecha
    result = []
    for dia in sorted(daily_summary.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')):
        data = daily_summary[dia]
        
        # Consolidar lista de extras
        all_extras_raw = ', '.join(data['extras_list'])
        
        result.append({
            'Dia': dia,
            'Ingreso Reservas': int(data['Ingreso Reservas']),
            'Ingreso extras': int(data['Ingreso extras']),
            'Costo Operativo': int(data['Costo Operativo']),
            'Costo marketing': int(data['Costo marketing']),
            'Costo Remuneracion': int(data['Costo Remuneracion']),
            'Costos Extras': int(data['Costos Extras']),
            'Extras': all_extras_raw if all_extras_raw else 'Sin extras'
        })
    
    return result

def generate_extras_summary(reservations_data: List[Dict[str, Any]], costs_dict: Dict[str, float], prices_dict: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Genera un resumen agregado de todos los extras vendidos
    """
    extras_summary = {}
    
    for reserva in reservations_data:
        extras_str = reserva.get('Extras', '')
        
        if extras_str == 'Sin extras':
            continue
        
        # Parsear la lista de extras
        import re
        extras_items = extras_str.split(', ')
        
        for item in extras_items:
            # Formato: "nombre_extra xCantidad"
            match = re.match(r'(.+?)\s+x(\d+)', item.strip())
            if not match:
                continue
            
            extra_name = match.group(1).strip()
            cantidad = int(match.group(2))
            
            # Buscar precio y costo
            precio_unitario = find_cost_for_extra(extra_name, prices_dict)
            costo_unitario = find_cost_for_extra(extra_name, costs_dict)
            
            # Agregar al resumen
            if extra_name not in extras_summary:
                extras_summary[extra_name] = {
                    'cantidad': 0,
                    'ingresos': 0,
                    'costos': 0
                }
            
            extras_summary[extra_name]['cantidad'] += cantidad
            extras_summary[extra_name]['ingresos'] += cantidad * precio_unitario
            extras_summary[extra_name]['costos'] += cantidad * costo_unitario
    
    # Convertir a lista ordenada por ingresos
    result = []
    for extra_name, data in sorted(extras_summary.items(), key=lambda x: x[1]['ingresos'], reverse=True):
        utilidad = data['ingresos'] - data['costos']
        result.append({
            'Extras vendidos': extra_name,
            'cantidad': data['cantidad'],
            'ingresos': int(data['ingresos']),
            'costos': int(data['costos']),
            'utilidad': int(utilidad)
        })
    
    return result

def main():
    if len(sys.argv) < 2:
        print("\nUso: python scripts/export_daily_analysis.py <fecha_inicio> [fecha_fin]")
        print("\nEjemplos:")
        print("  python scripts/export_daily_analysis.py 2026-01-01 2026-01-31")
        print("  python scripts/export_daily_analysis.py 2026-01-01  # Solo un dia")
        print("\nFormato de fecha: YYYY-MM-DD")
        return
    
    start_date_str = sys.argv[1]
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else start_date_str
    
    # Validar fechas
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Formato de fecha inválido. Use YYYY-MM-DD")
        return
    
    if start_date > end_date:
        print("Error: La fecha de inicio debe ser anterior a la fecha de fin")
        return
    
    settings = get_settings()
    
    print(f"\n{'='*70}")
    print(f"EXPORTANDO ANALISIS DIARIO DE RESERVAS")
    print(f"{'='*70}\n")
    print(f"Periodo: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    with psycopg.connect(settings.database_url) as conn:
        # Cargar costos y precios desde BD
        print("\nCargando costos y precios desde base de datos...")
        costs_dict, prices_dict = load_costs_and_prices_from_db(conn)
        print(f"Costos cargados: {len(costs_dict)} extras")
        print(f"Precios cargados: {len(prices_dict)} extras")
        
        # Cargar costos de marketing por fecha
        print("\nCargando costos de marketing...")
        marketing_query = """
            SELECT 
                cost_date,
                COALESCE(SUM(amount_spent), 0) as total_cost
            FROM marketing_costs
            WHERE cost_date BETWEEN %s AND %s
            GROUP BY cost_date
        """
        
        marketing_costs_by_date = {}
        with conn.cursor() as cur:
            cur.execute(marketing_query, (start_date_str, end_date_str))
            for row in cur.fetchall():
                cost_date = row[0]
                total_cost = float(row[1]) if row[1] else 0
                marketing_costs_by_date[cost_date] = total_cost
        
        print(f"Costos de marketing cargados para {len(marketing_costs_by_date)} días")
        
        # Obtener datos
        print("\nObteniendo datos de reservas...")
        data = get_reservations_data(conn, start_date_str, end_date_str, costs_dict, prices_dict, marketing_costs_by_date)
        print(f"Reservas encontradas: {len(data)}")
    
    if not data or len(data) == 0:
        print("\nNo se encontraron reservas en el período especificado.")
        return
    
    # Crear nombre de archivo
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    
    if start_date == end_date:
        filename = f"analisis_reservas_{start_date.strftime('%Y%m%d')}.csv"
    else:
        filename = f"analisis_reservas_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    output_path = output_dir / filename
    
    # Escribir CSV
    print(f"\nGenerando archivo CSV: {output_path}")
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'Dia', 'Id Reserva', 'Ingreso Reserva', 'Ingreso extras',
            'Costo Operativo', 'Costo Marketing', 'Costo Remuneracion', 'Costos Extras',
            'Extras', 'Nombre Cliente'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(data)
    
    # Mostrar resumen
    total_ingresos_reservas = sum(r['Ingreso Reserva'] for r in data)
    total_ingresos_extras = sum(r['Ingreso extras'] for r in data)
    total_costos_operativos = sum(r['Costo Operativo'] for r in data)
    total_costos_extras = sum(r['Costos Extras'] for r in data)
    
    print(f"\n{'='*70}")
    print(f"RESUMEN")
    print(f"{'='*70}")
    print(f"Total reservas: {len(data)}")
    print(f"Ingresos por reservas: ${total_ingresos_reservas:,.0f}")
    print(f"Ingresos por extras: ${total_ingresos_extras:,.0f}")
    print(f"Ingresos totales: ${total_ingresos_reservas + total_ingresos_extras:,.0f}")
    print(f"Costos operativos: ${total_costos_operativos:,.0f}")
    print(f"  (Fijos: ${18000 * len(data):,.0f}, Variables: ${total_costos_extras:,.0f})")
    
    # Generar resumen diario
    print(f"\n{'='*70}")
    print(f"GENERANDO RESUMEN DIARIO")
    print(f"{'='*70}\n")
    
    daily_summary = generate_daily_summary(data, marketing_costs_by_date)
    
    # Crear nombre de archivo para resumen diario
    if start_date == end_date:
        daily_filename = f"resumen_diario_{start_date.strftime('%Y%m%d')}.csv"
    else:
        daily_filename = f"resumen_diario_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    daily_output_path = output_dir / daily_filename
    
    # Escribir CSV de resumen diario
    with open(daily_output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['Dia', 'Ingreso Reservas', 'Ingreso extras', 'Costo Operativo', 
                     'Costo marketing', 'Costo Remuneracion', 'Costos Extras', 'Extras']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(daily_summary)
    
    print(f"Total de días con actividad: {len(daily_summary)}")
    print(f"Archivo de resumen diario generado en:")
    print(f"  {daily_output_path}")
    
    # Generar resumen de extras
    print(f"\n{'='*70}")
    print(f"GENERANDO RESUMEN DE EXTRAS")
    print(f"{'='*70}\n")
    
    extras_summary = generate_extras_summary(data, costs_dict, prices_dict)
    
    if extras_summary:
        # Crear nombre de archivo para resumen de extras
        if start_date == end_date:
            extras_filename = f"resumen_extras_{start_date.strftime('%Y%m%d')}.csv"
        else:
            extras_filename = f"resumen_extras_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        
        extras_output_path = output_dir / extras_filename
        
        # Escribir CSV de extras
        with open(extras_output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['Extras vendidos', 'cantidad', 'ingresos', 'costos', 'utilidad']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(extras_summary)
        
        print(f"Total de extras diferentes vendidos: {len(extras_summary)}")
        print(f"Archivo de extras generado en:")
        print(f"  {extras_output_path}")
    else:
        print("No se vendieron extras en este período")
    
    print(f"\n{'='*70}")
    print(f"ARCHIVOS GENERADOS")
    print(f"{'='*70}")
    print(f"1. Reservas detalladas:")
    print(f"   {output_path}")
    print(f"2. Resumen diario:")
    print(f"   {daily_output_path}")
    if extras_summary:
        print(f"3. Resumen de extras:")
        print(f"   {extras_output_path}")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
