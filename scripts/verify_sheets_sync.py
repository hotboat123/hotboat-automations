"""
Script para verificar datos sincronizados en Reservas_Con_Extras_Sheets
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
import json

DATABASE_URL = os.getenv('DATABASE_URL')

print("="*80)
print("VERIFICANDO SINCRONIZACIÓN A GOOGLE SHEETS")
print("="*80)

try:
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Total de registros
    cur.execute('SELECT COUNT(*) FROM "Reservas_Con_Extras_Sheets"')
    count = cur.fetchone()[0]
    print(f"\n[INFO] Total registros sincronizados: {count}")
    
    if count == 0:
        print("\n[WARNING] No hay datos sincronizados aún")
        print("[INFO] Ejecuta: railway run python scripts/test_sheets_sync.py")
    else:
        # Últimos registros
        cur.execute('''
            SELECT 
                raw->>'fecha' as fecha,
                raw->>'hora' as hora,
                raw->>'nombre_cliente' as cliente,
                raw->>'ingreso_total' as ingreso,
                updated_at
            FROM "Reservas_Con_Extras_Sheets"
            ORDER BY updated_at DESC
            LIMIT 5
        ''')
        
        print("\n[INFO] Últimos 5 registros sincronizados:")
        for row in cur.fetchall():
            print(f"  - {row[0]} {row[1]} | {row[2]} | ${float(row[3]):,.0f}")
        
        # Estadísticas por fecha
        cur.execute('''
            SELECT 
                raw->>'fecha' as fecha,
                COUNT(*) as registros,
                SUM((raw->>'ingreso_total')::numeric) as total_ingresos
            FROM "Reservas_Con_Extras_Sheets"
            GROUP BY raw->>'fecha'
            ORDER BY raw->>'fecha' DESC
            LIMIT 10
        ''')
        
        print("\n[INFO] Registros por fecha (últimas 10 fechas):")
        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]} reservas | ${float(row[2]):,.0f}")
    
    conn.close()
    print("\n[OK] Verificación completada")
    
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
