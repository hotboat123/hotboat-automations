"""
Script para ejecutar la migración 007 - Recrear tabla Reservas_Con_Extras_Sheets con formato columnar
"""
import sys
import os
import asyncio
from pathlib import Path

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        print("\n" + "="*80)
        print("EJECUTANDO MIGRACIÓN 007: Recrear Reservas_Con_Extras_Sheets (formato columnar)")
        print("="*80 + "\n")
        
        # Leer el archivo SQL
        migration_file = Path(__file__).parent.parent / 'database' / 'migrations' / '007_recreate_sheets_table_columnar.sql'
        
        if not migration_file.exists():
            print(f"ERROR: No se encontró el archivo {migration_file}")
            return
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        print("Ejecutando SQL...")
        print()
        
        # Ejecutar la migración
        await db.execute_non_query(sql)
        
        print("\n" + "="*80)
        print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*80)
        print()
        print("La tabla Reservas_Con_Extras_Sheets ahora tiene:")
        print("  - Columnas individuales (en vez de JSON gigante)")
        print("  - Mismo formato que reservas_con_extras")
        print("  - Más fácil de analizar y consultar")
        print()
        
    except Exception as e:
        print(f"\nERROR en la migración: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
