"""
Script para crear la tabla Reservas_Con_Extras_Sheets en Railway
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg

DATABASE_URL = os.getenv('DATABASE_URL')

print("="*80)
print("CREANDO TABLA Reservas_Con_Extras_Sheets")
print("="*80)

sql_file = Path(__file__).parent.parent / 'CREAR_TABLA_SHEETS.sql'
with open(sql_file, 'r', encoding='utf-8') as f:
    sql = f.read()

try:
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("\nEjecutando SQL...")
    cur.execute(sql)
    conn.commit()
    
    print("\n[OK] Tabla creada exitosamente!")
    
    # Verificar
    cur.execute("SELECT COUNT(*) FROM \"Reservas_Con_Extras_Sheets\"")
    count = cur.fetchone()[0]
    print(f"\n[INFO] Registros en tabla: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
