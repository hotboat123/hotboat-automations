"""
Script mejorado para exportar reservas con extras en formato diccionario JSON
Genera 2 CSVs:
1. Reservas cruzadas con extras en formato diccionario
2. Informacion Reservas sin cruce (huérfanas)
"""
import sys
import csv
import json
import psycopg
import re
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
    """Busca el costo de un extra"""
    extra_normalized = normalize_text(extra_name)
    
    if extra_normalized in costs_dict:
        return costs_dict[extra_normalized]
    
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
    
    words = [w for w in extra_normalized.split('_') if len(w) > 2]
    best_match = None
    best_score = 0
    
    for bd_name, bd_cost in costs_dict.items():
        if bd_cost == 0:
            continue
        score = sum(1 for word in words if word in bd_name)
        if score > best_score:
            best_score = score
            best_match = bd_cost
    
    if best_score >= 1:
        return best_match
    
    return 0

def load_costs_and_prices_from_db(conn) -> tuple[Dict[str, float], Dict[str, float], Dict[int, tuple]]:
    """
    Carga costos, precios y tabla de precios HotBoat desde la BD
    Retorna: (costs_dict, prices_dict, hotboat_prices_dict)
    donde hotboat_prices_dict = {num_personas: (precio, costo)}
    """
    costs = {}
    prices = {}
    hotboat_prices = {}
    
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
            
            try:
                costo = float(str(costo_str).replace('.', '').replace(',', '').strip()) if costo_str else 0
            except (ValueError, AttributeError):
                costo = 0
            
            try:
                precio = float(str(precio_str).replace('.', '').replace(',', '').strip()) if precio_str else 0
            except (ValueError, AttributeError):
                precio = 0
            
            normalized = normalize_text(extra_name)
            costs[normalized] = costo
            prices[normalized] = precio
            
            # Detectar precios base de HotBoat
            if 'hotboat' in extra_name.lower():
                import re
                # Buscar el número de personas: "HotBoat 2p" -> 2
                match = re.search(r'(\d+)p', extra_name, re.IGNORECASE)
                if match:
                    num_personas = int(match.group(1))
                    hotboat_prices[num_personas] = (precio, costo)
    
    return costs, prices, hotboat_prices

def extract_extras_dict(info_raw: Dict, costs_dict: Dict[str, float], prices_dict: Dict[str, float]) -> Dict[str, Any]:
    """
    Extrae los extras en formato diccionario
    Retorna: {
        'extras': {'nombre_extra': cantidad, ...},
        'ingreso_extras': float,
        'costo_extras': float
    }
    """
    extras_dict = {}
    ingreso_extras = 0
    costo_extras = 0
    
    if not info_raw:
        return {
            'extras': {},
            'ingreso_extras': 0,
            'costo_extras': 0
        }
    
    extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
    
    for key, value in info_raw.items():
        key_lower = key.lower()
        is_extra = any(key_lower.startswith(prefix) for prefix in extra_prefixes)
        
        if not is_extra:
            continue
        
        try:
            cantidad = int(str(value).strip()) if value and str(value).strip() else 0
        except (ValueError, AttributeError):
            cantidad = 0
        
        if cantidad <= 0:
            continue
        
        # Extraer nombre del extra
        alias_match = re.search(r'\[(.+?)\]', key)
        if alias_match:
            extra_name = alias_match.group(1)
        else:
            extra_name = key
        
        # Buscar precio y costo
        precio_unitario = find_cost_for_extra(extra_name, prices_dict)
        costo_unitario = find_cost_for_extra(extra_name, costs_dict)
        
        subtotal = cantidad * precio_unitario
        costo_total = cantidad * costo_unitario
        
        ingreso_extras += subtotal
        costo_extras += costo_total
        
        # Agregar al diccionario de extras
        extras_dict[extra_name] = cantidad
    
    return {
        'extras': extras_dict,
        'ingreso_extras': ingreso_extras,
        'costo_extras': costo_extras
    }

def get_reservations_with_extras(conn, start_date: str, end_date: str, costs_dict: Dict[str, float], prices_dict: Dict[str, float], hotboat_prices: Dict[int, tuple]) -> List[Dict[str, Any]]:
    """
    Obtiene las reservas cruzadas con sus extras
    Usa booknetic_appointments como fuente principal (igual que export_daily_analysis.py)
    """
    COSTO_FIJO_POR_RESERVA = 18000  # Gas + Leña + Agua + Hielo
    
    query = """
        WITH appointments_data AS (
            SELECT 
                ba.id as appointment_id,
                DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
                TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
                ba.raw->>'customer' as customer_name,
                ba.raw->>'email' as customer_email,
                ba.raw->>'phone' as customer_phone,
                ba.raw->>'service' as service_name,
                CAST(
                    REGEXP_REPLACE(
                        REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                        '[^0-9]',
                        '',
                        'g'
                    ) AS NUMERIC
                ) as payment_amount,
                ba.status,
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
                ) as horario_salida_normalized,
                ir.raw->>'nombre' as nombre_reserva,
                ir.raw->>'telefono' as telefono_reserva,
                ir.raw->>'cantidad_personas' as num_personas,
                ir.raw->>'ciudad_origen' as ciudad_origen,
                ir.raw->>'como_supieron_de_hotboat?' as como_supieron,
                ir.raw->>'clima_del_día' as clima_del_dia,
                ir.raw->>'categoría_clientes' as categoria_clientes,
                ir.raw->>'tipo_clientes' as tipo_clientes,
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
            ad.appointment_time as hora,
            ad.appointment_id,
            ad.customer_name,
            ad.customer_email,
            ad.customer_phone,
            ad.service_name,
            ad.payment_amount,
            ad.status,
            r.reservation_id,
            r.nombre_reserva,
            r.telefono_reserva,
            r.num_personas,
            r.ciudad_origen,
            r.como_supieron,
            r.clima_del_dia,
            r.categoria_clientes,
            r.tipo_clientes,
            r.extras_json
        FROM appointments_data ad
        LEFT JOIN reservations_with_extras r 
            ON ad.appointment_date = r.reservation_date
            AND ad.appointment_time = r.horario_salida_normalized
            AND ad.ba_row_num = r.ir_row_num
        ORDER BY ad.appointment_date, ad.appointment_time
    """
    
    results = []
    
    with conn.cursor() as cur:
        cur.execute(query, (start_date, end_date))
        
        for row in cur.fetchall():
            fecha = row[0]
            hora = row[1]
            appointment_id = row[2]
            customer_name = row[3] if row[3] else 'Sin nombre'
            customer_email = row[4] if row[4] else ''
            customer_phone = row[5] if row[5] else ''
            service_name = row[6] if row[6] else ''
            payment_amount = float(row[7]) if row[7] else 0
            status = row[8] if row[8] else ''
            reservation_id = row[9] if row[9] else ''
            nombre_reserva = row[10] if row[10] else ''
            telefono_reserva = row[11] if row[11] else ''
            num_personas = row[12] if row[12] else ''
            ciudad_origen = row[13] if row[13] else ''
            como_supieron = row[14] if row[14] else ''
            clima_del_dia = row[15] if row[15] else ''
            categoria_clientes = row[16] if row[16] else ''
            tipo_clientes = row[17] if row[17] else ''
            extras_json = row[18] if row[18] else {}
            
            # Extraer extras en formato diccionario
            extras_data = extract_extras_dict(extras_json, costs_dict, prices_dict)
            
            # Usar nombre de reserva si existe, sino customer_name
            nombre_final = nombre_reserva if nombre_reserva else customer_name
            telefono_final = telefono_reserva if telefono_reserva else customer_phone
            
            # Extraer adultos y niños del JSON
            adultos = 0
            ninos = 0
            
            if extras_json:
                # Buscar la clave de adultos
                for key in extras_json.keys():
                    if 'adult' in key.lower() and 'nombre' not in key.lower():
                        try:
                            val = extras_json[key]
                            if val and str(val).strip():
                                adultos = int(str(val).strip())
                                break
                        except (ValueError, AttributeError):
                            pass
                
                # Buscar la clave de niños
                for key in extras_json.keys():
                    if ('niño' in key.lower() or 'nino' in key.lower()) and 'nombre' not in key.lower():
                        try:
                            val = extras_json[key]
                            if val and str(val).strip():
                                ninos = int(str(val).strip())
                                break
                        except (ValueError, AttributeError):
                            pass
            
            # CALCULAR INGRESO BASE SEGÚN NÚMERO DE PERSONAS
            ingreso_base = 0
            
            # Intentar obtener número de personas
            # Prioridad: 1) adultos, 2) num_personas, 3) extraer del nombre del servicio
            num_personas_calculado = 2  # default
            
            if adultos > 0:
                num_personas_calculado = adultos
            elif num_personas and str(num_personas).isdigit():
                num_personas_calculado = int(num_personas)
            else:
                # Intentar extraer del nombre del servicio: "HotBoat Trip 5 people"
                import re
                if service_name:
                    match = re.search(r'(\d+)\s*people', service_name, re.IGNORECASE)
                    if match:
                        num_personas_calculado = int(match.group(1))
            
            # Buscar en tabla de precios HotBoat
            if num_personas_calculado in hotboat_prices:
                ingreso_base, _ = hotboat_prices[num_personas_calculado]
            else:
                # Si no está en la tabla, usar el payment como fallback
                ingreso_base = payment_amount if payment_amount else 0
                # Y restar los extras para no duplicar
                if ingreso_base > extras_data['ingreso_extras']:
                    ingreso_base -= extras_data['ingreso_extras']
            
            ingreso_total = ingreso_base + extras_data['ingreso_extras']
            
            results.append({
                'Fecha': fecha.strftime('%d/%m/%Y') if fecha else '',
                'Hora': hora[:5] if hora else '',  # Solo HH:MM
                'Nombre Cliente': nombre_final,
                'Servicio': service_name,
                'Ingreso Reserva': int(ingreso_base),
                'Ingreso Extras': int(extras_data['ingreso_extras']),
                'Ingreso Total': int(ingreso_total),
                'Costo Operativo Fijo': COSTO_FIJO_POR_RESERVA,
                'Costo Operativo Variable': int(extras_data['costo_extras']),
                'Costo Operativo Total': int(COSTO_FIJO_POR_RESERVA + extras_data['costo_extras']),
                'Num Adultos': adultos,
                'Num Ninos': ninos,
                'Ciudad Origen': ciudad_origen,
                'Como Supieron': como_supieron,
                'Clima del Dia': clima_del_dia,
                'Tipo Clientes': tipo_clientes,
                'ID Appointment': str(appointment_id)[:8],
                'ID Reserva': str(reservation_id)[:8] if reservation_id else '',
                'Email': customer_email,
                'Telefono': telefono_final,
                'Num Personas': num_personas,
                'Categoria Clientes': categoria_clientes,
                'Status': status,
                'Extras (JSON)': json.dumps(extras_data['extras'], ensure_ascii=False),
                'Tiene Cruce': 'Si' if reservation_id else 'No'
            })
    
    return results

def get_orphan_info_reservas(conn, start_date: str, end_date: str, costs_dict: Dict[str, float], prices_dict: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Obtiene las "Informacion Reservas" que NO se cruzaron con ningún appointment
    """
    query = """
        WITH appointments_data AS (
            SELECT 
                DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
                TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                 TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                    ORDER BY ba.id
                ) as ba_row_num
            FROM booknetic_appointments ba
            WHERE (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
        ),
        reservations_with_row AS (
            SELECT 
                ir.id,
                TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                ir.raw->>'horario_salida' as horario_salida_original,
                -- Normalizar hora a formato HH24:MI:SS
                TO_CHAR(
                    TO_TIMESTAMP(ir.raw->>'horario_salida', 'HH24:MI:SS'),
                    'HH24:MI:SS'
                ) as horario_salida_normalized,
                ir.raw->>'nombre' as nombre,
                ir.raw->>'apellido' as apellido,
                ir.raw->>'telefono' as telefono,
                ir.raw->>'email' as email,
                ir.raw->>'cantidad_personas' as num_personas,
                ir.raw as extras_json,
                ir.created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                 TO_CHAR(TO_TIMESTAMP(ir.raw->>'horario_salida', 'HH24:MI:SS'), 'HH24:MI:SS')
                    ORDER BY ir.created_at ASC
                ) as ir_row_num
            FROM "Informacion Reservas" ir
            WHERE ir.raw->>'fecha' IS NOT NULL
                AND TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') BETWEEN %s AND %s
        )
        SELECT 
            r.id,
            r.reservation_date,
            r.horario_salida_original,
            r.nombre,
            r.apellido,
            r.telefono,
            r.email,
            r.num_personas,
            r.extras_json,
            r.created_at
        FROM reservations_with_row r
        WHERE NOT EXISTS (
            SELECT 1 FROM appointments_data ad
            WHERE ad.appointment_date = r.reservation_date
            AND ad.appointment_time = r.horario_salida_normalized
            AND ad.ba_row_num = r.ir_row_num
        )
        ORDER BY r.reservation_date, r.horario_salida_normalized
    """
    
    results = []
    
    with conn.cursor() as cur:
        cur.execute(query, (start_date, end_date))
        
        for row in cur.fetchall():
            reservation_id = row[0]
            fecha = row[1]
            hora = row[2]
            nombre = row[3] if row[3] else ''
            apellido = row[4] if row[4] else ''
            telefono = row[5] if row[5] else ''
            email = row[6] if row[6] else ''
            num_personas = row[7] if row[7] else ''
            extras_json = row[8] if row[8] else {}
            created_at = row[9]
            
            # Extraer extras
            extras_data = extract_extras_dict(extras_json, costs_dict, prices_dict)
            
            nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else 'Sin nombre'
            
            # Extraer adultos y niños del JSON (buscando por diferentes nombres de clave)
            adultos = 0
            ninos = 0
            
            if extras_json:
                # Buscar la clave de adultos (puede tener diferentes nombres)
                for key in extras_json.keys():
                    if 'adult' in key.lower() and 'nombre' not in key.lower():
                        try:
                            val = extras_json[key]
                            if val and str(val).strip():
                                adultos = int(str(val).strip())
                                break
                        except (ValueError, AttributeError):
                            pass
                
                # Buscar la clave de niños
                for key in extras_json.keys():
                    if ('niño' in key.lower() or 'nino' in key.lower()) and 'nombre' not in key.lower():
                        try:
                            val = extras_json[key]
                            if val and str(val).strip():
                                ninos = int(str(val).strip())
                                break
                        except (ValueError, AttributeError):
                            pass
            
            results.append({
                'ID Reserva': str(reservation_id)[:8],
                'Fecha': fecha.strftime('%d/%m/%Y') if fecha else '',
                'Hora': hora if hora else '',
                'Nombre': nombre_completo,
                'Telefono': telefono,
                'Email': email,
                'Num Personas': num_personas,
                'Num Adultos': adultos,
                'Num Ninos': ninos,
                'Ingreso Extras': int(extras_data['ingreso_extras']),
                'Costo Extras': int(extras_data['costo_extras']),
                'Extras (JSON)': json.dumps(extras_data['extras'], ensure_ascii=False),
                'Creado': created_at.strftime('%d/%m/%Y %H:%M') if created_at else '',
                'Motivo': 'No se encontro appointment con misma fecha/hora'
            })
    
    return results

def main():
    if len(sys.argv) < 2:
        print("\nUso: python scripts/export_reservas_con_extras.py <fecha_inicio> [fecha_fin]")
        print("\nEjemplos:")
        print("  python scripts/export_reservas_con_extras.py 2026-01-01 2026-01-31")
        print("  python scripts/export_reservas_con_extras.py 2026-01-18")
        print("\nFormato de fecha: YYYY-MM-DD")
        return
    
    start_date_str = sys.argv[1]
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else start_date_str
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Formato de fecha invalido. Use YYYY-MM-DD")
        return
    
    if start_date > end_date:
        print("Error: La fecha de inicio debe ser anterior a la fecha de fin")
        return
    
    settings = get_settings()
    
    print(f"\n{'='*80}")
    print(f"EXPORTANDO RESERVAS CON EXTRAS (FORMATO JSON)")
    print(f"{'='*80}\n")
    print(f"Periodo: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    with psycopg.connect(settings.database_url) as conn:
        # Cargar precios y costos
        print("\nCargando costos, precios y tabla HotBoat...")
        costs_dict, prices_dict, hotboat_prices = load_costs_and_prices_from_db(conn)
        print(f"[OK] {len(costs_dict)} costos, {len(prices_dict)} precios, {len(hotboat_prices)} precios HotBoat cargados")
        
        # Obtener reservas cruzadas
        print("\nObteniendo reservas cruzadas...")
        reservas = get_reservations_with_extras(conn, start_date_str, end_date_str, costs_dict, prices_dict, hotboat_prices)
        print(f"[OK] {len(reservas)} reservas encontradas")
        
        # Obtener info reservas huerfanas
        print("\nBuscando Informacion Reservas sin cruce...")
        huerfanas = get_orphan_info_reservas(conn, start_date_str, end_date_str, costs_dict, prices_dict)
        print(f"[OK] {len(huerfanas)} registros sin cruce encontrados")
    
    # Crear archivos
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    
    if start_date == end_date:
        base_filename = f"reservas_extras_{start_date.strftime('%Y%m%d')}"
    else:
        base_filename = f"reservas_extras_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    # CSV 1: Reservas cruzadas
    csv1_path = output_dir / f"{base_filename}.csv"
    
    if reservas:
        with open(csv1_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=reservas[0].keys())
            writer.writeheader()
            writer.writerows(reservas)
        
        print(f"\n[OK] CSV de reservas cruzadas generado:")
        print(f"    {csv1_path}")
    else:
        print(f"\n[!] No se encontraron reservas en el periodo")
    
    # CSV 2: Info Reservas huerfanas
    csv2_path = output_dir / f"{base_filename}_huerfanas.csv"
    
    if huerfanas:
        with open(csv2_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=huerfanas[0].keys())
            writer.writeheader()
            writer.writerows(huerfanas)
        
        print(f"[OK] CSV de registros sin cruce generado:")
        print(f"    {csv2_path}")
    else:
        print(f"[OK] Todos los registros de Informacion Reservas tienen cruce")
    
    # Resumen
    print(f"\n{'='*80}")
    print(f"RESUMEN")
    print(f"{'='*80}")
    print(f"Total reservas:                {len(reservas)}")
    
    con_cruce = sum(1 for r in reservas if r['Tiene Cruce'] == 'Si')
    sin_cruce = sum(1 for r in reservas if r['Tiene Cruce'] == 'No')
    
    print(f"  - Con cruce a Info Reservas:  {con_cruce} ({con_cruce/len(reservas)*100:.1f}%)")
    print(f"  - Sin cruce a Info Reservas:  {sin_cruce} ({sin_cruce/len(reservas)*100:.1f}%)")
    
    print(f"\nInfo Reservas huerfanas:       {len(huerfanas)}")
    
    if reservas:
        total_ingreso = sum(r['Ingreso Total'] for r in reservas)
        total_extras = sum(r['Ingreso Extras'] for r in reservas)
        
        print(f"\nIngreso total:                 ${total_ingreso:,.0f}")
        print(f"Ingreso por extras:            ${total_extras:,.0f}")
        print(f"Porcentaje extras:             {total_extras/total_ingreso*100:.1f}%")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
