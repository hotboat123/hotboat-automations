"""
Script para ver detalles de las entradas incompletas de Informacion Reservas del 10/03
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
import json
from app.config import get_settings

settings = get_settings()
conn = psycopg.connect(settings.database_url)

target_date = '10/03/2026'

print(f"\nEntradas de INFORMACION RESERVAS para {target_date}:")
print("="*80)

with conn.cursor() as cur:
    cur.execute("""
        SELECT id, raw
        FROM "Informacion Reservas"
        WHERE raw->>'fecha' = %s
        ORDER BY id
    """, (target_date,))
    
    entries = cur.fetchall()
    
    print(f"\nTotal: {len(entries)} entradas\n")
    
    for entry_id, raw in entries:
        print(f"\n{'='*80}")
        print(f"ID: {entry_id}")
        print(f"{'='*80}")
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        print()

conn.close()

print("\n" + "="*80)
print("DIAGNOSTICO:")
print("="*80)
print("Estas entradas están INCOMPLETAS (sin hora, sin datos).")
print("Por eso NO pueden hacer cruce con los appointments.")
print()
print("SOLUCIÓN:")
print("1. Eliminar estas entradas vacías de la BD")
print("2. O completarlas con la información correcta de las 3 reservas del 10/03")
print("="*80)
