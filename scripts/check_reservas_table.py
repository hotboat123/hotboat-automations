"""
Script para verificar datos en reservas_con_extras
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg

DATABASE_URL = os.getenv('DATABASE_URL')

print("="*80)
print("VERIFICANDO TABLA reservas_con_extras")
print("="*80)

try:
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Total de registros
    cur.execute("SELECT COUNT(*), MIN(fecha), MAX(fecha) FROM reservas_con_extras")
    result = cur.fetchone()
    print(f"\nTotal registros: {result[0]}")
    print(f"Fecha minima: {result[1]}")
    print(f"Fecha maxima: {result[2]}")
    
    # Registros de ayer
    yesterday = (datetime.now() - timedelta(days=1)).date()
    cur.execute("SELECT COUNT(*) FROM reservas_con_extras WHERE fecha = %s", (yesterday,))
    count_yesterday = cur.fetchone()[0]
    print(f"\nRegistros de ayer ({yesterday}): {count_yesterday}")
    
    if count_yesterday > 0:
        cur.execute("""
            SELECT 
                appointment_id,
                nombre_cliente,
                servicio,
                ingreso_total,
                tiene_cruce
            FROM reservas_con_extras 
            WHERE fecha = %s
            ORDER BY hora
            LIMIT 5
        """, (yesterday,))
        
        print("\nPrimeros 5 registros de ayer:")
        for row in cur.fetchall():
            print(f"  - {row[1]} | {row[2]} | ${row[3]:,.0f} | Cruce: {'Si' if row[4] else 'No'}")
    
    # Registros de hoy
    today = datetime.now().date()
    cur.execute("SELECT COUNT(*) FROM reservas_con_extras WHERE fecha = %s", (today,))
    count_today = cur.fetchone()[0]
    print(f"\nRegistros de hoy ({today}): {count_today}")
    
    conn.close()
    print("\n[OK] Verificacion completada")
    
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
