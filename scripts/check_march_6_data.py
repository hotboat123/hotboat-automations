"""
Script para verificar los datos del 6 de marzo en reservas_con_extras
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

async def check_march_6():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        # Ver appointments del 6 de marzo
        print("\n" + "="*80)
        print("APPOINTMENTS - 6 MARZO 2026")
        print("="*80 + "\n")
        
        appt_query = """
            SELECT 
                id,
                status,
                raw->>'customer_name' as customer_name,
                raw->>'service' as service,
                raw->>'start_date' as start_date,
                raw->>'payment' as payment,
                raw->>'service_extras' as service_extras
            FROM booknetic_appointments
            WHERE DATE(TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = '2026-03-06'
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
            print(f"  Service Extras: {appt['service_extras']}")
            print(f"  Status: {appt['status']}")
            print()
        
        # Ver Informacion Reservas del 6 de marzo
        print("\n" + "="*80)
        print("INFORMACION RESERVAS - 6 MARZO 2026")
        print("="*80 + "\n")
        
        ir_query = """
            SELECT 
                id,
                raw->>'fecha' as fecha,
                raw->>'horario_salida' as horario_salida,
                raw->>'nombre' as nombre,
                raw->>'n°_de_adultos' as adultos,
                raw->>'n°_niños' as ninos
            FROM "Informacion Reservas"
            WHERE TO_DATE(raw->>'fecha', 'DD/MM/YYYY') = '2026-03-06'
            ORDER BY raw->>'horario_salida', id
        """
        
        reservas = await db.execute_query(ir_query)
        print(f"Total Informacion Reservas: {len(reservas)}\n")
        
        for res in reservas:
            print(f"ID: {res['id'][:20]}...")
            print(f"  Horario: {res['horario_salida']}")
            print(f"  Nombre: {res['nombre']}")
            print(f"  Adultos: {res['adultos']}, Niños: {res['ninos']}")
            print()
        
        # Ver resultado en reservas_con_extras
        print("\n" + "="*80)
        print("RESERVAS_CON_EXTRAS - 6 MARZO 2026")
        print("="*80 + "\n")
        
        rce_query = """
            SELECT 
                appointment_id,
                fecha,
                hora,
                nombre_cliente,
                servicio,
                num_personas,
                num_adultos,
                num_ninos,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                costo_operativo_fijo,
                costo_operativo_variable,
                costo_operativo_total,
                extras_json,
                tiene_cruce
            FROM reservas_con_extras
            WHERE fecha = '2026-03-06'
            ORDER BY hora
        """
        
        reservas_con_extras = await db.execute_query(rce_query)
        print(f"Total en reservas_con_extras: {len(reservas_con_extras)}\n")
        
        for i, r in enumerate(reservas_con_extras, 1):
            print(f"\n--- RESERVA #{i} (Appointment ID: {r['appointment_id']}) ---")
            print(f"Cliente: {r['nombre_cliente']}")
            print(f"Hora: {r['hora']}")
            print(f"Servicio: {r['servicio']}")
            print(f"Personas: {r['num_personas']} (Adultos: {r['num_adultos']}, Ninos: {r['num_ninos']})")
            print(f"Tiene cruce: {r['tiene_cruce']}")
            print(f"\nINGRESOS:")
            print(f"  - Ingreso Reserva: ${r['ingreso_reserva']:,.0f}")
            print(f"  - Ingreso Extras: ${r['ingreso_extras']:,.0f}")
            print(f"  - Ingreso TOTAL: ${r['ingreso_total']:,.0f}")
            print(f"\nCOSTOS:")
            print(f"  - Costo Fijo: ${r['costo_operativo_fijo']:,.0f}")
            print(f"  - Costo Variable: ${r['costo_operativo_variable']:,.0f}")
            print(f"  - Costo TOTAL: ${r['costo_operativo_total']:,.0f}")
            
            if r['extras_json']:
                print(f"\nEXTRAS:")
                extras = r['extras_json'] if isinstance(r['extras_json'], dict) else {}
                for extra_name, cantidad in extras.items():
                    print(f"  - {extra_name}: {cantidad}")
        
        # Totales
        print(f"\n{'='*80}")
        print(f"TOTALES DEL 6 DE MARZO")
        print(f"{'='*80}")
        
        total_query = """
            SELECT 
                COUNT(*) as num_reservas,
                SUM(ingreso_reserva) as total_ingreso_reserva,
                SUM(ingreso_extras) as total_ingreso_extras,
                SUM(ingreso_total) as total_ingreso_total,
                SUM(costo_operativo_fijo) as total_costo_fijo,
                SUM(costo_operativo_variable) as total_costo_variable,
                SUM(costo_operativo_total) as total_costo_total
            FROM reservas_con_extras
            WHERE fecha = '2026-03-06'
        """
        
        totals = await db.execute_query(total_query)
        if totals:
            t = totals[0]
            print(f"\nNumero de reservas: {t['num_reservas']}")
            print(f"\nIngresos:")
            print(f"  - Por Reservas: ${t['total_ingreso_reserva']:,.0f}")
            print(f"  - Por Extras: ${t['total_ingreso_extras']:,.0f}")
            print(f"  - TOTAL: ${t['total_ingreso_total']:,.0f}")
            print(f"\nCostos:")
            print(f"  - Fijos: ${t['total_costo_fijo']:,.0f}")
            print(f"  - Variables: ${t['total_costo_variable']:,.0f}")
            print(f"  - TOTAL: ${t['total_costo_total']:,.0f}")
            print(f"\nUtilidad: ${t['total_ingreso_total'] - t['total_costo_total']:,.0f}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_march_6())
