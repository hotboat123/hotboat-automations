"""
Script de demostración visual del cruce de tablas
Muestra paso a paso cómo se hace el cruce para una fecha específica
"""
import sys
import psycopg
from pathlib import Path
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings

def print_section(title: str):
    """Imprime un separador de sección"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def demo_cruce_tablas(fecha_str: str):
    """
    Demuestra visualmente el cruce de tablas para una fecha específica
    """
    settings = get_settings()
    
    print_section(f"DEMOSTRACION DEL CRUCE DE TABLAS - {fecha_str}")
    
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            
            # Paso 1: Obtener appointments
            print_section("PASO 1: Datos de booknetic_appointments")
            
            query_appointments = """
                SELECT 
                    ba.id,
                    DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as fecha,
                    TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as hora,
                    ba.raw->>'customer' as cliente,
                    ba.raw->>'service' as servicio,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                     TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                        ORDER BY ba.id
                    ) as row_num
                FROM booknetic_appointments ba
                WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = %s
                    AND (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
                ORDER BY fecha, hora
            """
            
            cur.execute(query_appointments, (fecha_str,))
            appointments = cur.fetchall()
            
            if not appointments:
                print(f"[!] No se encontraron appointments para {fecha_str}")
                return
            
            print(f"Encontrados: {len(appointments)} appointments\n")
            print(f"{'ID':<10} {'Fecha':<12} {'Hora':<10} {'Cliente':<30} {'ROW_NUM':<8}")
            print("-" * 80)
            for apt in appointments:
                apt_id = str(apt[0])[:8]
                fecha = apt[1].strftime('%d/%m/%Y')
                hora = apt[2]
                cliente = apt[3][:28] if apt[3] else 'Sin nombre'
                row_num = apt[5]
                print(f"{apt_id:<10} {fecha:<12} {hora:<10} {cliente:<30} {row_num:<8}")
            
            # Paso 2: Obtener payments
            print_section("PASO 2: Datos de booknetic_payments")
            
            query_payments = """
                SELECT 
                    bp.id,
                    DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as fecha,
                    TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as hora,
                    CAST(
                        REGEXP_REPLACE(
                            REPLACE(COALESCE(bp.raw->>'payment', '0'), '$', ''),
                            '[^0-9]',
                            '',
                            'g'
                        ) AS NUMERIC
                    ) as monto,
                    bp.raw->>'status' as estado,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')),
                                     TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                        ORDER BY bp.id
                    ) as row_num
                FROM booknetic_payments bp
                WHERE DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) = %s
                ORDER BY fecha, hora
            """
            
            cur.execute(query_payments, (fecha_str,))
            payments = cur.fetchall()
            
            print(f"Encontrados: {len(payments)} payments\n")
            print(f"{'ID':<10} {'Fecha':<12} {'Hora':<10} {'Monto':<12} {'Estado':<20} {'ROW_NUM':<8}")
            print("-" * 80)
            for pmt in payments:
                pmt_id = str(pmt[0])[:8]
                fecha = pmt[1].strftime('%d/%m/%Y')
                hora = pmt[2]
                monto = f"${int(pmt[3]):,}" if pmt[3] else "$0"
                estado = pmt[4][:18] if pmt[4] else 'Sin estado'
                row_num = pmt[5]
                print(f"{pmt_id:<10} {fecha:<12} {hora:<10} {monto:<12} {estado:<20} {row_num:<8}")
            
            # Paso 3: Obtener Informacion Reservas
            print_section("PASO 3: Datos de Informacion Reservas")
            
            query_info = """
                SELECT 
                    ir.id,
                    TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as fecha,
                    ir.raw->>'horario_salida' as hora,
                    ir.raw->>'nombre' as nombre,
                    ir.raw->>'cantidad_personas' as personas,
                    ROW_NUMBER() OVER (
                        PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                     ir.raw->>'horario_salida'
                        ORDER BY ir.created_at ASC
                    ) as row_num
                FROM "Informacion Reservas" ir
                WHERE TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') = %s
                ORDER BY fecha, hora
            """
            
            cur.execute(query_info, (fecha_str,))
            info_reservas = cur.fetchall()
            
            print(f"Encontrados: {len(info_reservas)} registros en Informacion Reservas\n")
            print(f"{'ID':<10} {'Fecha':<12} {'Hora':<10} {'Nombre':<30} {'Personas':<10} {'ROW_NUM':<8}")
            print("-" * 80)
            for info in info_reservas:
                info_id = str(info[0])[:8]
                fecha = info[1].strftime('%d/%m/%Y')
                hora = info[2] if info[2] else 'Sin hora'
                nombre = info[3][:28] if info[3] else 'Sin nombre'
                personas = info[4] if info[4] else '0'
                row_num = info[5]
                print(f"{info_id:<10} {fecha:<12} {hora:<10} {nombre:<30} {personas:<10} {row_num:<8}")
            
            # Paso 4: Mostrar el cruce
            print_section("PASO 4: RESULTADO DEL CRUCE (JOIN)")
            
            query_cruce = """
                WITH appointments_data AS (
                    SELECT 
                        ba.id as apt_id,
                        DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as fecha,
                        TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as hora,
                        ba.raw->>'customer' as cliente,
                        ROW_NUMBER() OVER (
                            PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                         TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                            ORDER BY ba.id
                        ) as row_num
                    FROM booknetic_appointments ba
                    WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = %s
                        AND (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
                ),
                payments_data AS (
                    SELECT 
                        bp.id as pmt_id,
                        DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as fecha,
                        TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as hora,
                        ROW_NUMBER() OVER (
                            PARTITION BY DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')),
                                         TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                            ORDER BY bp.id
                        ) as row_num
                    FROM booknetic_payments bp
                    WHERE DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) = %s
                ),
                info_data AS (
                    SELECT 
                        ir.id as info_id,
                        TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as fecha,
                        ir.raw->>'horario_salida' as hora,
                        ir.raw->>'nombre' as nombre,
                        ROW_NUMBER() OVER (
                            PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                         ir.raw->>'horario_salida'
                            ORDER BY ir.created_at ASC
                        ) as row_num
                    FROM "Informacion Reservas" ir
                    WHERE TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') = %s
                )
                SELECT 
                    ad.apt_id,
                    pd.pmt_id,
                    id.info_id,
                    ad.fecha,
                    ad.hora,
                    ad.cliente,
                    id.nombre,
                    ad.row_num
                FROM appointments_data ad
                LEFT JOIN payments_data pd
                    ON ad.fecha = pd.fecha
                    AND ad.hora = pd.hora
                    AND ad.row_num = pd.row_num
                LEFT JOIN info_data id
                    ON ad.fecha = id.fecha
                    AND ad.hora = id.hora
                    AND ad.row_num = id.row_num
                ORDER BY ad.fecha, ad.hora, ad.row_num
            """
            
            cur.execute(query_cruce, (fecha_str, fecha_str, fecha_str))
            cruces = cur.fetchall()
            
            print(f"Total de reservas cruzadas: {len(cruces)}\n")
            print("Leyenda:")
            print("  [OK]  = Cruce exitoso (las 3 tablas tienen datos)")
            print("  [P-]  = Sin datos en Payment")
            print("  [I-]  = Sin datos en Informacion Reservas")
            print("  [PI-] = Sin datos en Payment ni Informacion Reservas\n")
            
            print(f"{'ID Apt':<10} {'ID Pmt':<10} {'ID Info':<10} {'Fecha':<12} {'Hora':<10} {'Cliente':<25} {'ROW':<5} {'Estado':<6}")
            print("-" * 100)
            
            for cruce in cruces:
                apt_id = str(cruce[0])[:8] if cruce[0] else '-'
                pmt_id = str(cruce[1])[:8] if cruce[1] else '-'
                info_id = str(cruce[2])[:8] if cruce[2] else '-'
                fecha = cruce[3].strftime('%d/%m/%Y')
                hora = cruce[4]
                cliente = cruce[5][:23] if cruce[5] else 'Sin nombre'
                row_num = cruce[7]
                
                # Determinar estado del cruce
                if pmt_id != '-' and info_id != '-':
                    estado = '[OK]'
                elif pmt_id == '-' and info_id == '-':
                    estado = '[PI-]'
                elif pmt_id == '-':
                    estado = '[P-]'
                else:
                    estado = '[I-]'
                
                print(f"{apt_id:<10} {pmt_id:<10} {info_id:<10} {fecha:<12} {hora:<10} {cliente:<25} {row_num:<5} {estado:<6}")
            
            # Estadísticas
            print_section("ESTADISTICAS DEL CRUCE")
            
            total = len(cruces)
            con_payment = sum(1 for c in cruces if c[1] is not None)
            con_info = sum(1 for c in cruces if c[2] is not None)
            completos = sum(1 for c in cruces if c[1] is not None and c[2] is not None)
            
            print(f"Total de reservas (appointments): {total}")
            print(f"Con datos de payment:              {con_payment} ({con_payment/total*100:.1f}%)")
            print(f"Con datos de info reservas:        {con_info} ({con_info/total*100:.1f}%)")
            print(f"Cruces completos (3 tablas):       {completos} ({completos/total*100:.1f}%)")
            
            print(f"\n{'='*80}\n")

def main():
    if len(sys.argv) < 2:
        print("\nUso: python scripts/demo_cruce_tablas.py <fecha>")
        print("\nEjemplo:")
        print("  python scripts/demo_cruce_tablas.py 2026-01-11")
        print("\nFormato de fecha: YYYY-MM-DD")
        return
    
    fecha_str = sys.argv[1]
    
    # Validar fecha
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
    except ValueError:
        print("Error: Formato de fecha invalido. Use YYYY-MM-DD")
        return
    
    demo_cruce_tablas(fecha_str)

if __name__ == "__main__":
    main()
