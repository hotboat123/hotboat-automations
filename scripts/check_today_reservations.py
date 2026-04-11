"""
Script para verificar las reservas de hoy y el cruce con Informacion Reservas
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from app.config import get_settings
from datetime import datetime, date

settings = get_settings()
conn = psycopg.connect(settings.database_url)

today = date.today()
print(f"\nVerificando reservas para HOY: {today.strftime('%Y-%m-%d')}")
print("="*80)

# 1. Verificar reservas en appointments para hoy
print("\n1. APPOINTMENTS para hoy:")
print("-"*80)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            id,
            raw->>'start_date' as fecha,
            raw->>'start_time' as hora,
            customer_name,
            service_name,
            raw->>'payment_amount' as payment_amount
        FROM booknetic_appointments
        WHERE raw->>'start_date' = %s
        ORDER BY raw->>'start_time'
    """, (today.strftime('%Y-%m-%d'),))
    
    appointments = cur.fetchall()
    
    if appointments:
        for apt in appointments:
            print(f"ID: {apt[0]}")
            print(f"  Fecha/Hora: {apt[1]} {apt[2]}")
            print(f"  Cliente: {apt[3]}")
            print(f"  Servicio: {apt[4]}")
            print(f"  Payment: ${apt[5]}")
            print()
    else:
        print("NO HAY APPOINTMENTS PARA HOY")

# 2. Verificar si hay info en "Informacion Reservas" para hoy
print("\n2. INFORMACION RESERVAS para hoy:")
print("-"*80)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            raw->>'fecha' as fecha,
            raw->>'hora' as hora,
            raw->>'nombre_cliente' as nombre,
            raw->>'servicio' as servicio
        FROM "Informacion Reservas"
        WHERE raw->>'fecha' = %s
        ORDER BY raw->>'hora'
    """, (today.strftime('%d/%m/%Y'),))
    
    info_reservas = cur.fetchall()
    
    if info_reservas:
        for info in info_reservas:
            print(f"Fecha/Hora: {info[0]} {info[1]}")
            print(f"  Cliente: {info[2]}")
            print(f"  Servicio: {info[3]}")
            print()
    else:
        print("NO HAY INFORMACION RESERVAS PARA HOY")

# 3. Verificar tabla reservas_con_extras para hoy
print("\n3. RESERVAS_CON_EXTRAS para hoy:")
print("-"*80)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            appointment_id,
            fecha,
            hora,
            nombre_cliente,
            servicio,
            ingreso_reserva,
            ingreso_extras,
            ingreso_total,
            tiene_cruce
        FROM reservas_con_extras
        WHERE fecha = %s
        ORDER BY hora
    """, (today,))
    
    reservas = cur.fetchall()
    
    if reservas:
        total_con_cruce = sum(1 for r in reservas if r[8])
        total_sin_cruce = sum(1 for r in reservas if not r[8])
        
        print(f"Total reservas: {len(reservas)}")
        print(f"  - Con cruce: {total_con_cruce}")
        print(f"  - Sin cruce: {total_sin_cruce}")
        print()
        
        for r in reservas:
            print(f"Appointment ID: {r[0]}")
            print(f"  Fecha/Hora: {r[1]} {r[2]}")
            print(f"  Cliente: {r[3]}")
            print(f"  Servicio: {r[4]}")
            print(f"  Ingreso reserva: ${r[5]:,.0f}")
            print(f"  Ingreso extras: ${r[6]:,.0f}")
            print(f"  Ingreso total: ${r[7]:,.0f}")
            print(f"  Tiene cruce: {'SI' if r[8] else 'NO'}")
            print()
    else:
        print("NO HAY RESERVAS_CON_EXTRAS PARA HOY")

conn.close()

print("\n" + "="*80)
print("DIAGNOSTICO COMPLETADO")
print("="*80)
