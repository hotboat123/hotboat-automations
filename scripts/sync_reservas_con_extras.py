"""
Script para sincronizar la tabla reservas_con_extras
Lee los datos cruzados y los guarda en la tabla materializada
"""
import sys
import json
import psycopg
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings

# Constantes
COSTO_FIJO_POR_RESERVA = 18000  # Gas + Leña + Agua + Hielo

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
                precio = float(str(precio_str).replace('.', '').replace(',', '').strip())
            except (ValueError, AttributeError):
                precio = 0
            
            normalized = normalize_text(extra_name)
            
            # Si hay duplicados, quedarnos con el precio/costo más alto (más actual)
            if normalized in costs:
                costs[normalized] = max(costs[normalized], costo)
            else:
                costs[normalized] = costo
            
            if normalized in prices:
                prices[normalized] = max(prices[normalized], precio)
            else:
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
        # Champañas - mapear riccadonna (doble n) a riccadona (una n)
        'champana_riccadonna_ruby': 'champana_riccadona',
        'champana_riccadonna_asti': 'champana_riccadona',
        'champana_riccadonna_moscato_rose': 'champana_riccadona',
        'champana_riccadonna': 'champana_riccadona',
        # Hora extra - variantes del formulario
        'hora_extra': 'hora_extra',
        'hora_adicional': 'hora_extra',
        'hora_extra_de_navegacion': 'hora_extra',
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

def find_price_for_extra(extra_name: str, prices_dict: Dict[str, float]) -> float:
    """Busca el precio de un extra (misma lógica que costos)"""
    return find_cost_for_extra(extra_name, prices_dict)  # Reutiliza la misma lógica

def extract_extras_dict(extras_json: Dict[str, Any], costs_dict: Dict[str, float], prices_dict: Dict[str, float]) -> Dict[str, Any]:
    """
    Extrae los extras del JSON y calcula costos e ingresos
    Retorna: {
        'extras': {"nombre": cantidad, ...},
        'ingreso_extras': float,
        'costo_extras': float
    }
    """
    if not extras_json:
        return {'extras': {}, 'ingreso_extras': 0, 'costo_extras': 0}
    
    extras_dict = {}
    ingreso_total = 0
    costo_total = 0
    
    extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
    
    for key, value in extras_json.items():
        key_lower = key.lower()
        
        if not any(key_lower.startswith(prefix) for prefix in extra_prefixes):
            continue
        
        try:
            quantity = int(str(value).strip()) if value and str(value).strip() else 0
        except (ValueError, AttributeError):
            quantity = 0
        
        if quantity <= 0:
            continue
        
        import re
        alias_match = re.search(r'\[(.+?)\]', key)
        if alias_match:
            alias = alias_match.group(1)
        else:
            alias = key
        
        # Buscar precio y costo
        price = find_price_for_extra(alias, prices_dict)
        cost = find_cost_for_extra(alias, costs_dict)
        
        # Calcular totales
        ingreso_total += price * quantity
        costo_total += cost * quantity
        
        # Agregar al diccionario
        extras_dict[alias] = quantity
    
    return {
        'extras': extras_dict,
        'ingreso_extras': ingreso_total,
        'costo_extras': costo_total
    }

def sync_reservas_con_extras(start_date: str = None, end_date: str = None, force_recreate: bool = False):
    """
    Sincroniza la tabla reservas_con_extras con los datos actuales
    
    Args:
        start_date: Fecha inicial (YYYY-MM-DD), por defecto: hace 30 días
        end_date: Fecha final (YYYY-MM-DD), por defecto: hoy
        force_recreate: Si True, borra y recrea todos los registros
    """
    settings = get_settings()
    
    # Fechas por defecto
    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    
    if not start_date:
        from datetime import timedelta
        start = date.today() - timedelta(days=30)
        start_date = start.strftime('%Y-%m-%d')
    
    print(f"\n{'='*80}")
    print(f"SINCRONIZANDO TABLA reservas_con_extras")
    print(f"{'='*80}\n")
    print(f"Periodo: {start_date} - {end_date}")
    print(f"Modo: {'Recrear todo' if force_recreate else 'Actualizar incremental'}\n")
    
    try:
        conn = psycopg.connect(settings.database_url)
        
        # Cargar costos y precios
        print("Cargando costos, precios y tabla HotBoat...")
        costs_dict, prices_dict, hotboat_prices = load_costs_and_prices_from_db(conn)
        print(f"[OK] {len(costs_dict)} costos, {len(prices_dict)} precios, {len(hotboat_prices)} precios HotBoat cargados\n")
        
        # Si force_recreate, borrar datos del periodo
        if force_recreate:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM reservas_con_extras
                    WHERE fecha BETWEEN %s AND %s
                """, (start_date, end_date))
                deleted = cur.rowcount
                conn.commit()
                print(f"[OK] Borrados {deleted} registros existentes\n")
        
        # Query principal (misma lógica que export_reservas_con_extras.py)
        query = """
            WITH appointments_data AS (
                SELECT 
                    ba.id::text as appointment_id,
                    DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
                    TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
                    -- Booknetic guarda el nombre en raw->>'customer' (igual que export_reservas_con_extras.py)
                    COALESCE(
                        NULLIF(TRIM(ba.raw->>'customer'), ''),
                        NULLIF(TRIM(ba.raw->>'customer_name'), '')
                    ) as customer_name,
                    COALESCE(
                        NULLIF(TRIM(ba.raw->>'email'), ''),
                        NULLIF(TRIM(ba.raw->>'customer_email'), '')
                    ) as customer_email,
                    COALESCE(
                        NULLIF(TRIM(ba.raw->>'phone'), ''),
                        NULLIF(TRIM(ba.raw->>'customer_phone_number'), '')
                    ) as customer_phone,
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
                    ir.id::text as reservation_id,
                    TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
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
        
        print("Obteniendo datos cruzados...")
        with conn.cursor() as cur:
            cur.execute(query, (start_date, end_date))
            rows = cur.fetchall()
        
        print(f"[OK] {len(rows)} reservas obtenidas\n")
        
        if not rows:
            print("No hay datos para sincronizar.")
            return
        
        # Procesar e insertar/actualizar
        print("Procesando y guardando en base de datos...")
        inserted = 0
        updated = 0
        
        with conn.cursor() as cur:
            for row in rows:
                fecha = row[0]
                hora = row[1]
                appointment_id = row[2]
                customer_name = row[3]
                customer_email = row[4]
                customer_phone = row[5]
                service_name = row[6]
                payment_amount = row[7] or 0
                status = row[8]
                reservation_id = row[9]
                nombre_reserva = row[10]
                telefono_reserva = row[11]
                num_personas = row[12]
                ciudad_origen = row[13]
                como_supieron = row[14]
                clima_del_dia = row[15]
                categoria_clientes = row[16]
                tipo_clientes = row[17]
                extras_json = row[18] if row[18] else {}
                
                # Usar nombre de reserva si existe
                nombre_final = nombre_reserva if nombre_reserva else customer_name
                telefono_final = telefono_reserva if telefono_reserva else customer_phone
                
                # Extraer adultos y niños del JSON
                adultos = 0
                ninos = 0
                
                if extras_json:
                    for key in extras_json.keys():
                        if 'adult' in key.lower() and 'nombre' not in key.lower():
                            try:
                                val = extras_json[key]
                                if val and str(val).strip():
                                    adultos = int(str(val).strip())
                                    break
                            except (ValueError, AttributeError):
                                pass
                    
                    for key in extras_json.keys():
                        if ('niño' in key.lower() or 'nino' in key.lower()) and 'nombre' not in key.lower():
                            try:
                                val = extras_json[key]
                                if val and str(val).strip():
                                    ninos = int(str(val).strip())
                                    break
                            except (ValueError, AttributeError):
                                pass
                
                # Extraer extras y calcular costos/ingresos
                extras_data = extract_extras_dict(extras_json, costs_dict, prices_dict)
                
                ingreso_extras = float(extras_data['ingreso_extras'])
                costo_variable = float(extras_data['costo_extras'])
                
                # CALCULAR INGRESO BASE SEGÚN NÚMERO DE PERSONAS
                ingreso_base = 0
                costo_base = 0
                
                # EXCEPCIÓN: Si payment_amount es 0, no hay ingreso
                if not payment_amount or payment_amount == 0:
                    ingreso_base = 0
                    ingreso_extras = 0  # Tampoco cobrar extras si no hay pago
                else:
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
                        ingreso_base, costo_base = hotboat_prices[num_personas_calculado]
                    else:
                        # Si no está en la tabla, usar el payment como fallback
                        ingreso_base = float(payment_amount) if payment_amount else 0
                        # Y restar los extras para no duplicar
                        if ingreso_base > ingreso_extras:
                            ingreso_base -= ingreso_extras
                
                ingreso_total = float(ingreso_base) + ingreso_extras
                costo_total = COSTO_FIJO_POR_RESERVA + costo_variable
                tiene_cruce = bool(reservation_id)
                
                # Convertir extras a JSON
                extras_json_str = json.dumps(extras_data['extras'])
                
                # Insertar o actualizar
                cur.execute("""
                    INSERT INTO reservas_con_extras (
                        appointment_id, reservation_id, fecha, hora,
                        nombre_cliente, email, telefono,
                        servicio, num_personas,
                        ingreso_reserva, ingreso_extras, ingreso_total,
                        costo_operativo_fijo, costo_operativo_variable, costo_operativo_total,
                        num_adultos, num_ninos,
                        ciudad_origen, como_supieron, clima_del_dia,
                        categoria_clientes, tipo_clientes,
                        status, tiene_cruce, extras_json
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s::jsonb
                    )
                    ON CONFLICT (appointment_id, fecha) 
                    DO UPDATE SET
                        reservation_id = EXCLUDED.reservation_id,
                        hora = EXCLUDED.hora,
                        nombre_cliente = EXCLUDED.nombre_cliente,
                        email = EXCLUDED.email,
                        telefono = EXCLUDED.telefono,
                        servicio = EXCLUDED.servicio,
                        num_personas = EXCLUDED.num_personas,
                        ingreso_reserva = EXCLUDED.ingreso_reserva,
                        ingreso_extras = EXCLUDED.ingreso_extras,
                        ingreso_total = EXCLUDED.ingreso_total,
                        costo_operativo_variable = EXCLUDED.costo_operativo_variable,
                        costo_operativo_total = EXCLUDED.costo_operativo_total,
                        num_adultos = EXCLUDED.num_adultos,
                        num_ninos = EXCLUDED.num_ninos,
                        ciudad_origen = EXCLUDED.ciudad_origen,
                        como_supieron = EXCLUDED.como_supieron,
                        clima_del_dia = EXCLUDED.clima_del_dia,
                        categoria_clientes = EXCLUDED.categoria_clientes,
                        tipo_clientes = EXCLUDED.tipo_clientes,
                        status = EXCLUDED.status,
                        tiene_cruce = EXCLUDED.tiene_cruce,
                        extras_json = EXCLUDED.extras_json,
                        updated_at = NOW()
                """, (
                    appointment_id, reservation_id, fecha, hora,
                    nombre_final, customer_email, telefono_final,
                    service_name, num_personas,
                    ingreso_base, ingreso_extras, ingreso_total,
                    COSTO_FIJO_POR_RESERVA, costo_variable, costo_total,
                    adultos, ninos,
                    ciudad_origen, como_supieron, clima_del_dia,
                    categoria_clientes, tipo_clientes,
                    status, tiene_cruce, extras_json_str
                ))
                
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    updated += 1
        
        conn.commit()
        conn.close()
        
        print(f"\n[OK] Sincronización completada:")
        print(f"  - Insertados: {inserted}")
        print(f"  - Actualizados: {updated}")
        print(f"  - Total procesados: {len(rows)}\n")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sincroniza la tabla reservas_con_extras')
    parser.add_argument('start_date', nargs='?', help='Fecha inicial (YYYY-MM-DD), por defecto: hace 30 días')
    parser.add_argument('end_date', nargs='?', help='Fecha final (YYYY-MM-DD), por defecto: hoy')
    parser.add_argument('--force', action='store_true', help='Borrar y recrear registros existentes')
    
    args = parser.parse_args()
    
    exit_code = sync_reservas_con_extras(
        start_date=args.start_date,
        end_date=args.end_date,
        force_recreate=args.force
    )
    
    sys.exit(exit_code)
