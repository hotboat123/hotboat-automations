"""
Verificar si el cruce está funcionando correctamente
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from app.config import get_settings

settings = get_settings()
conn = psycopg.connect(settings.database_url)

print("\nDATOS PARA EL CRUCE DEL 10/03/2026:")
print("="*80)

# Ver appointments con la hora normalizada
print("\nAPPOINTMENTS (con hora normalizada):")
print("-"*80)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            id,
            raw->>'start_date' as fecha_original,
            TO_CHAR(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as hora_normalizada
        FROM booknetic_appointments
        WHERE DATE(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = '2026-03-10'
        ORDER BY TO_CHAR(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
    """)
    
    for row in cur.fetchall():
        print(f"  ID {row[0]}: {row[1]} -> {row[2]}")

# Ver Informacion Reservas con la hora normalizada
print("\nINFORMACION RESERVAS (con hora normalizada):")
print("-"*80)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            id,
            raw->>'fecha' as fecha,
            raw->>'horario_salida' as horario_original,
            TO_CHAR(TO_TIMESTAMP(raw->>'horario_salida', 'HH24:MI:SS'), 'HH24:MI:SS') as hora_normalizada,
            raw->>'nombre' as nombre,
            raw->>'n°_de_adultos' as adultos
        FROM "Informacion Reservas"
        WHERE raw->>'fecha' = '10/03/2026'
        ORDER BY TO_CHAR(TO_TIMESTAMP(raw->>'horario_salida', 'HH24:MI:SS'), 'HH24:MI:SS')
    """)
    
    for row in cur.fetchall():
        print(f"  {row[1]} {row[2]} -> {row[3]}")
        print(f"    Nombre: '{row[4]}', Adultos: {row[5]}")

conn.close()

print("\n" + "="*80)
print("ANÁLISIS:")
print("="*80)
print("Si las horas normalizadas coinciden, el cruce debería funcionar.")
print("El problema podría ser que la tabla reservas_con_extras NO se ha actualizado")
print("después de que se llenaron estos formularios.")
print("\nSOLUCIÓN: Ejecutar el script de sincronización:")
print("  python scripts/sync_reservas_con_extras.py 2026-03-10 2026-03-10 --force")
print("="*80)
