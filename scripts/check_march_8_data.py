"""
Script para verificar los datos del 8 de marzo - caso de 5 personas
"""
import sys
import os
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def check_march_8():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        print("\n" + "="*80)
        print("APPOINTMENTS - 8 MARZO 2026")
        print("="*80 + "\n")
        
        appt_query = """
            SELECT 
                id,
                raw->>'customer_name' as customer_name,
                raw->>'service' as service,
                raw->>'start_date' as start_date,
                raw->>'payment' as payment,
                raw
            FROM booknetic_appointments
            WHERE DATE(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = '2026-03-08'
            ORDER BY TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')
        """
        
        appointments = await db.execute_query(appt_query)
        print(f"Total appointments: {len(appointments)}\n")
        
        for appt in appointments:
            print(f"ID: {appt['id']}")
            print(f"  Cliente: {appt['customer_name']}")
            print(f"  Servicio: {appt['service']}")
            print(f"  Fecha: {appt['start_date']}")
            print(f"  Payment: {appt['payment']}")
            print()
        
        print("\n" + "="*80)
        print("INFORMACION RESERVAS - 8 MARZO 2026")
        print("="*80 + "\n")
        
        ir_query = """
            SELECT 
                id,
                raw->>'fecha' as fecha,
                raw->>'horario_salida' as horario,
                raw->>'nombre' as nombre,
                raw->>'cantidad_personas' as cantidad_personas,
                raw->>'n°_de_adultos' as adultos,
                raw->>'n°_niños' as ninos
            FROM "Informacion Reservas"
            WHERE TO_DATE(raw->>'fecha', 'DD/MM/YYYY') = '2026-03-08'
            ORDER BY raw->>'horario_salida'
        """
        
        reservas = await db.execute_query(ir_query)
        print(f"Total Informacion Reservas: {len(reservas)}\n")
        
        for res in reservas:
            print(f"ID: {res['id'][:20]}...")
            print(f"  Horario: {res['horario']}")
            print(f"  Nombre: {res['nombre']}")
            print(f"  Cantidad personas: {res['cantidad_personas']}")
            print(f"  Adultos: {res['adultos']}")
            print(f"  Ninos: {res['ninos']}")
            print()
        
        print("\n" + "="*80)
        print("RESERVAS_CON_EXTRAS - 8 MARZO 2026")
        print("="*80 + "\n")
        
        rce_query = """
            SELECT 
                appointment_id,
                hora,
                servicio,
                num_personas,
                num_adultos,
                num_ninos,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total
            FROM reservas_con_extras
            WHERE fecha = '2026-03-08'
            ORDER BY hora
        """
        
        reservas_con_extras = await db.execute_query(rce_query)
        print(f"Total: {len(reservas_con_extras)}\n")
        
        for r in reservas_con_extras:
            print(f"Appointment {r['appointment_id']} - {r['hora']}")
            print(f"  Servicio: {r['servicio']}")
            print(f"  Num Personas: {r['num_personas']}")
            print(f"  Adultos: {r['num_adultos']}, Ninos: {r['num_ninos']}")
            print(f"  Ingreso Reserva: ${r['ingreso_reserva']:,.0f}")
            print(f"  Ingreso Extras: ${r['ingreso_extras']:,.0f}")
            print(f"  Ingreso Total: ${r['ingreso_total']:,.0f}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_march_8())
