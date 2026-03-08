"""
Script para exportar TODA la información consolidada de reservas a CSV
Incluye datos de appointments, payments, Informacion Reservas y cálculos de costos/ingresos
"""
import sys
import csv
import psycopg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from decimal import Decimal

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

def get_full_reservations_data(conn, start_date: str, end_date: str, costs_dict: Dict[str, float], prices_dict: Dict[str, float], marketing_costs_by_date: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Obtiene TODOS los datos consolidados de reservas para el rango de fechas especificado
    Incluye información de appointments, payments e Informacion Reservas
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
                TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
                TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
                ba.raw->>'customer' as customer_name,
                ba.raw->>'email' as customer_email,
                ba.raw->>'phone' as customer_phone,
                ba.raw->>'service' as service_name,
                ba.raw->>'location' as location,
                ba.status,
                ba.created_at as appointment_created_at,
                ba.raw as appointment_raw,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                 TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                    ORDER BY ba.id
                ) as ba_row_num
            FROM booknetic_appointments ba
            WHERE (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
                AND DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) BETWEEN %s AND %s
        ),
        payments_data AS (
            SELECT 
                bp.id as payment_id,
                DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as payment_date,
                TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI') as payment_datetime,
                TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as payment_time,
                CAST(
                    REGEXP_REPLACE(
                        REPLACE(COALESCE(bp.raw->>'payment', '0'), '$', ''),
                        '[^0-9]',
                        '',
                        'g'
                    ) AS NUMERIC
                ) as payment_amount,
                bp.raw->>'status' as payment_status,
                bp.raw->>'method' as payment_method,
                bp.raw as payment_raw,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')),
                                 TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                    ORDER BY bp.id
                ) as bp_row_num
            FROM booknetic_payments bp
            WHERE bp.raw->>'appointment_date' IS NOT NULL
                AND DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) BETWEEN %s AND %s
        ),
        reservations_with_extras AS (
            SELECT 
                ir.id as reservation_id,
                TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                ir.raw->>'horario_salida' as horario_salida,
                ir.raw->>'nombre' as nombre_reserva,
                ir.raw->>'apellido' as apellido_reserva,
                ir.raw->>'telefono' as telefono_reserva,
                ir.raw->>'email' as email_reserva,
                ir.raw->>'cantidad_personas' as num_personas,
                ir.raw->>'descuento' as descuento,
                ir.raw->>'notas' as notas,
                ir.created_at as info_created_at,
                ir.raw as extras_json,
                ROW_NUMBER() OVER (
                    PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                 ir.raw->>'horario_salida'
                    ORDER BY ir.created_at ASC
                ) as ir_row_num
            FROM "Informacion Reservas" ir
            WHERE ir.raw->>'fecha' IS NOT NULL
        )
        SELECT 
            -- Datos de appointment
            ad.appointment_id,
            ad.appointment_date as fecha,
            ad.appointment_time as hora,
            ad.customer_name,
            ad.customer_email,
            ad.customer_phone,
            ad.service_name,
            ad.location,
            ad.status as appointment_status,
            ad.appointment_created_at,
            ad.appointment_raw,
            
            -- Datos de payment
            pd.payment_id,
            pd.payment_amount,
            pd.payment_status,
            pd.payment_method,
            pd.payment_raw,
            
            -- Datos de Informacion Reservas
            r.reservation_id,
            r.nombre_reserva,
            r.apellido_reserva,
            r.telefono_reserva,
            r.email_reserva,
            r.num_personas,
            r.descuento,
            r.notas,
            r.info_created_at,
            r.extras_json
            
        FROM appointments_data ad
        LEFT JOIN payments_data pd
            ON ad.appointment_date = pd.payment_date
            AND ad.appointment_time = pd.payment_time
            AND ad.ba_row_num = pd.bp_row_num
        LEFT JOIN reservations_with_extras r 
            ON ad.appointment_date = r.reservation_date
            AND ad.appointment_time = r.horario_salida
            AND ad.ba_row_num = r.ir_row_num
        ORDER BY ad.appointment_date, ad.appointment_datetime
    """
    
    results = []
    
    with conn.cursor() as cur:
        cur.execute(query, (start_date, end_date, start_date, end_date))
        
        for row in cur.fetchall():
            # Extraer datos del row
            appointment_id = row[0] if row[0] else ''
            fecha = row[1]
            hora = row[2] if row[2] else ''
            customer_name = row[3] if row[3] else ''
            customer_email = row[4] if row[4] else ''
            customer_phone = row[5] if row[5] else ''
            service_name = row[6] if row[6] else ''
            location = row[7] if row[7] else ''
            appointment_status = row[8] if row[8] else ''
            appointment_created_at = row[9] if row[9] else None
            appointment_raw = row[10] if row[10] else {}
            
            payment_id = row[11] if row[11] else ''
            payment_amount = float(row[12]) if row[12] else 0
            payment_status = row[13] if row[13] else ''
            payment_method = row[14] if row[14] else ''
            payment_raw = row[15] if row[15] else {}
            
            reservation_id = row[16] if row[16] else ''
            nombre_reserva = row[17] if row[17] else ''
            apellido_reserva = row[18] if row[18] else ''
            telefono_reserva = row[19] if row[19] else ''
            email_reserva = row[20] if row[20] else ''
            num_personas_str = row[21] if row[21] else ''
            descuento_str = row[22] if row[22] else ''
            notas = row[23] if row[23] else ''
            info_created_at = row[24] if row[24] else None
            extras_json = row[25] if row[25] else {}
            
            # Procesar número de personas
            try:
                num_personas = int(str(num_personas_str).strip()) if num_personas_str else 0
            except (ValueError, AttributeError):
                num_personas = 0
            
            # Procesar descuento
            try:
                descuento_percent = float(str(descuento_str).strip().replace('%', '')) if descuento_str else 0
            except (ValueError, AttributeError):
                descuento_percent = 0
            
            # Procesar extras
            extras_list = []
            extras_detalle = []
            ingreso_extras = 0
            costo_extras_total = 0
            
            if extras_json:
                extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
                
                for key, value in extras_json.items():
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
                    
                    # Extraer nombre del extra
                    import re
                    alias_match = re.search(r'\[(.+?)\]', key)
                    if alias_match:
                        extra_name = alias_match.group(1)
                    else:
                        extra_name = key
                    
                    # Buscar precio de venta
                    precio_unitario = find_cost_for_extra(extra_name, prices_dict)
                    subtotal = cantidad * precio_unitario
                    ingreso_extras += subtotal
                    
                    # Buscar costo
                    costo_unitario = find_cost_for_extra(extra_name, costs_dict)
                    costo_total_extra = cantidad * costo_unitario
                    costo_extras_total += costo_total_extra
                    
                    # Agregar a lista
                    if cantidad > 0:
                        extras_list.append(f"{extra_name} x{cantidad}")
                        extras_detalle.append({
                            'nombre': extra_name,
                            'cantidad': cantidad,
                            'precio_unitario': precio_unitario,
                            'costo_unitario': costo_unitario,
                            'subtotal': subtotal,
                            'costo_total': costo_total_extra
                        })
            
            # Calcular costos y utilidades
            ingreso_reserva = payment_amount
            costo_operativo_fijo = COSTO_FIJO_POR_RESERVA
            costo_operativo_variable = costo_extras_total
            costo_operativo_total = costo_operativo_fijo + costo_operativo_variable
            
            # Obtener costo de marketing
            costo_marketing = marketing_costs_by_date.get(fecha, 0)
            
            # Calcular ingresos y utilidades
            ingreso_total = ingreso_reserva + ingreso_extras
            costo_total = costo_operativo_total + costo_marketing
            utilidad_bruta = ingreso_total - costo_operativo_total
            utilidad_neta = ingreso_total - costo_total
            
            # Margen de utilidad
            margen_bruto = (utilidad_bruta / ingreso_total * 100) if ingreso_total > 0 else 0
            margen_neto = (utilidad_neta / ingreso_total * 100) if ingreso_total > 0 else 0
            
            # Formatear extras
            extras_str = ", ".join(extras_list) if extras_list else "Sin extras"
            
            # Nombre completo del cliente
            if nombre_reserva or apellido_reserva:
                nombre_completo = f"{nombre_reserva} {apellido_reserva}".strip()
            else:
                nombre_completo = customer_name
            
            # Email y teléfono (priorizar de Informacion Reservas)
            email_final = email_reserva if email_reserva else customer_email
            telefono_final = telefono_reserva if telefono_reserva else customer_phone
            
            results.append({
                # Identificadores
                'Fecha': fecha.strftime('%d/%m/%Y') if fecha else '',
                'Hora': hora[:5] if hora else '',  # Solo HH:MM
                'ID Appointment': appointment_id[:8] if appointment_id else '',
                'ID Payment': payment_id[:8] if payment_id else '',
                'ID Reserva': reservation_id[:8] if reservation_id else '',
                
                # Información del cliente
                'Nombre Cliente': nombre_completo,
                'Email': email_final,
                'Telefono': telefono_final,
                
                # Información de la reserva
                'Servicio': service_name,
                'Ubicacion': location,
                'Num Personas': num_personas,
                'Descuento %': descuento_percent,
                'Notas': notas,
                
                # Ingresos
                'Ingreso Reserva': int(ingreso_reserva),
                'Ingreso Extras': int(ingreso_extras),
                'Ingreso Total': int(ingreso_total),
                
                # Costos
                'Costo Op Fijo': int(costo_operativo_fijo),
                'Costo Op Variable': int(costo_operativo_variable),
                'Costo Op Total': int(costo_operativo_total),
                'Costo Marketing': int(costo_marketing),
                'Costo Total': int(costo_total),
                
                # Utilidades
                'Utilidad Bruta': int(utilidad_bruta),
                'Utilidad Neta': int(utilidad_neta),
                'Margen Bruto %': round(margen_bruto, 1),
                'Margen Neto %': round(margen_neto, 1),
                
                # Extras
                'Extras': extras_str,
                
                # Status
                'Status Appointment': appointment_status,
                'Status Payment': payment_status,
                'Metodo Pago': payment_method,
                
                # Timestamps
                'Creado Appointment': appointment_created_at.strftime('%d/%m/%Y %H:%M') if appointment_created_at else '',
                'Creado Info Reserva': info_created_at.strftime('%d/%m/%Y %H:%M') if info_created_at else '',
            })
    
    return results

def main():
    if len(sys.argv) < 2:
        print("\nUso: python scripts/export_reservations_full.py <fecha_inicio> [fecha_fin]")
        print("\nEjemplos:")
        print("  python scripts/export_reservations_full.py 2026-01-01 2026-01-31")
        print("  python scripts/export_reservations_full.py 2026-01-01  # Solo un día")
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
    
    print(f"\n{'='*80}")
    print(f"EXPORTANDO INFORMACIÓN COMPLETA DE RESERVAS")
    print(f"{'='*80}\n")
    print(f"Periodo: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    with psycopg.connect(settings.database_url) as conn:
        # Cargar costos y precios
        print("\nCargando costos y precios desde base de datos...")
        costs_dict, prices_dict = load_costs_and_prices_from_db(conn)
        print(f"[OK] Costos cargados: {len(costs_dict)} extras")
        print(f"[OK] Precios cargados: {len(prices_dict)} extras")
        
        # Cargar costos de marketing
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
        
        print(f"[OK] Costos de marketing cargados para {len(marketing_costs_by_date)} dias")
        
        # Obtener datos completos
        print("\nObteniendo informacion consolidada de reservas...")
        data = get_full_reservations_data(conn, start_date_str, end_date_str, costs_dict, prices_dict, marketing_costs_by_date)
        print(f"[OK] Reservas encontradas: {len(data)}")
    
    if not data or len(data) == 0:
        print("\n[AVISO] No se encontraron reservas en el periodo especificado.")
        return
    
    # Crear archivo CSV
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    
    if start_date == end_date:
        filename = f"reservas_completas_{start_date.strftime('%Y%m%d')}.csv"
    else:
        filename = f"reservas_completas_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    output_path = output_dir / filename
    
    # Escribir CSV
    print(f"\nGenerando archivo CSV...")
    
    fieldnames = [
        'Fecha', 'Hora', 'ID Appointment', 'ID Payment', 'ID Reserva',
        'Nombre Cliente', 'Email', 'Telefono',
        'Servicio', 'Ubicacion', 'Num Personas', 'Descuento %', 'Notas',
        'Ingreso Reserva', 'Ingreso Extras', 'Ingreso Total',
        'Costo Op Fijo', 'Costo Op Variable', 'Costo Op Total', 'Costo Marketing', 'Costo Total',
        'Utilidad Bruta', 'Utilidad Neta', 'Margen Bruto %', 'Margen Neto %',
        'Extras',
        'Status Appointment', 'Status Payment', 'Metodo Pago',
        'Creado Appointment', 'Creado Info Reserva'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    # Mostrar resumen
    total_ingresos = sum(r['Ingreso Total'] for r in data)
    total_ingresos_reservas = sum(r['Ingreso Reserva'] for r in data)
    total_ingresos_extras = sum(r['Ingreso Extras'] for r in data)
    total_costos = sum(r['Costo Total'] for r in data)
    total_utilidad_neta = sum(r['Utilidad Neta'] for r in data)
    
    print(f"\n{'='*80}")
    print(f"RESUMEN")
    print(f"{'='*80}")
    print(f"Total reservas:          {len(data)}")
    print(f"\nINGRESOS:")
    print(f"  Reservas:              ${total_ingresos_reservas:>12,.0f}")
    print(f"  Extras:                ${total_ingresos_extras:>12,.0f}")
    print(f"  ---------------------------------")
    print(f"  TOTAL INGRESOS:        ${total_ingresos:>12,.0f}")
    print(f"\nCOSTOS:")
    print(f"  Operativos + Marketing:${total_costos:>12,.0f}")
    print(f"\nUTILIDAD:")
    print(f"  Utilidad Neta:         ${total_utilidad_neta:>12,.0f}")
    
    margen_promedio = (total_utilidad_neta / total_ingresos * 100) if total_ingresos > 0 else 0
    print(f"  Margen Neto:           {margen_promedio:>12.1f}%")
    
    promedio_por_reserva = total_ingresos / len(data) if len(data) > 0 else 0
    print(f"\nPromedio por reserva:    ${promedio_por_reserva:>12,.0f}")
    
    print(f"\n{'='*80}")
    print(f"ARCHIVO GENERADO")
    print(f"{'='*80}")
    print(f"{output_path}")
    print(f"\n[OK] Archivo CSV generado exitosamente con {len(data)} reservas")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
