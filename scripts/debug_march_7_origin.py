"""
Script para revisar TODOS los datos origen del 7 de marzo
"""
import sys
import os
import asyncio
import json

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def check_origin_data():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        print("\n" + "="*80)
        print("APPOINTMENTS - 7 MARZO 2026")
        print("="*80 + "\n")
        
        # Ver appointments
        appt_query = """
            SELECT 
                id,
                status,
                raw->>'customer_name' as customer_name,
                raw->>'service' as service,
                raw->>'start_date' as start_date,
                raw->>'payment' as payment,
                raw
            FROM booknetic_appointments
            WHERE DATE(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = '2026-03-07'
            ORDER BY id
        """
        
        appointments = await db.execute_query(appt_query)
        print(f"Total appointments: {len(appointments)}\n")
        
        for appt in appointments:
            print(f"ID: {appt['id']}")
            print(f"  Cliente: {appt['customer_name']}")
            print(f"  Servicio: {appt['service']}")
            print(f"  Fecha: {appt['start_date']}")
            print(f"  Payment: {appt['payment']}")
            print(f"  Status: {appt['status']}")
            
            # Ver el raw JSON completo
            raw = appt['raw']
            if raw:
                print(f"  RAW JSON:")
                for key, value in raw.items():
                    if key not in ['customer_name', 'service', 'start_date', 'payment']:
                        print(f"    {key}: {value}")
            print()
        
        print("\n" + "="*80)
        print("INFORMACION RESERVAS - 7 MARZO 2026")
        print("="*80 + "\n")
        
        # Ver Informacion Reservas
        ir_query = """
            SELECT 
                id,
                raw->>'fecha' as fecha,
                raw->>'horario_salida' as horario_salida,
                raw->>'nombre' as nombre,
                raw->>'cantidad_personas' as cantidad_personas,
                raw
            FROM "Informacion Reservas"
            WHERE TO_DATE(raw->>'fecha', 'DD/MM/YYYY') = '2026-03-07'
            ORDER BY id
        """
        
        reservas = await db.execute_query(ir_query)
        print(f"Total Informacion Reservas: {len(reservas)}\n")
        
        for res in reservas:
            print(f"ID: {res['id']}")
            print(f"  Fecha: {res['fecha']}")
            print(f"  Horario salida: {res['horario_salida']}")
            print(f"  Nombre: {res['nombre']}")
            print(f"  Personas: {res['cantidad_personas']}")
            
            # Ver todos los campos del raw
            raw = res['raw']
            if raw:
                print(f"  RAW JSON completo:")
                for key, value in sorted(raw.items()):
                    print(f"    {key}: {value}")
            print()
        
        print("\n" + "="*80)
        print("PRECIOS EXTRAS (para referencia)")
        print("="*80 + "\n")
        
        # Ver precios extras
        precios_query = """
            SELECT 
                raw->>'Extra' as extra_name,
                raw->>'Precio' as precio,
                raw->>'costo' as costo
            FROM "Precios Extras"
            WHERE raw->>'Extra' IS NOT NULL
            ORDER BY raw->>'Extra'
        """
        
        precios = await db.execute_query(precios_query)
        print(f"Total Precios Extras: {len(precios)}\n")
        
        for precio in precios:
            if precio['extra_name']:
                print(f"{precio['extra_name']}: Precio=${precio['precio']}, Costo=${precio['costo']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_origin_data())
