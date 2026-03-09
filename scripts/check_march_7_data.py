"""
Script para verificar los datos del 7 de marzo en reservas_con_extras
"""
import sys
import os
import asyncio
from datetime import datetime

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv
import json

load_dotenv()

async def check_march_7():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        # Obtener datos del 7 de marzo
        query = """
            SELECT 
                appointment_id,
                fecha,
                hora,
                nombre_cliente,
                servicio,
                num_personas,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                costo_operativo_fijo,
                costo_operativo_variable,
                costo_operativo_total,
                num_adultos,
                num_ninos,
                extras_json
            FROM reservas_con_extras
            WHERE fecha = '2026-03-07'
            ORDER BY hora
        """
        
        reservas = await db.execute_query(query)
        
        print(f"\n{'='*80}")
        print(f"RESERVAS DEL 7 DE MARZO 2026")
        print(f"{'='*80}\n")
        print(f"Total de reservas: {len(reservas)}\n")
        
        for i, r in enumerate(reservas, 1):
            print(f"\n--- RESERVA #{i} (ID: {r['appointment_id']}) ---")
            print(f"Cliente: {r['nombre_cliente']}")
            print(f"Hora: {r['hora']}")
            print(f"Servicio: {r['servicio']}")
            print(f"Personas: {r['num_personas']} (Adultos: {r['num_adultos']}, Niños: {r['num_ninos']})")
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
                for extra_name, extra_data in extras.items():
                    if isinstance(extra_data, dict):
                        print(f"  - {extra_name}: {extra_data.get('cantidad', 0)} x ${extra_data.get('precio', 0):,.0f} = ${extra_data.get('total', 0):,.0f}")
        
        # Totales del día
        print(f"\n{'='*80}")
        print(f"TOTALES DEL DÍA")
        print(f"{'='*80}")
        
        total_query = """
            SELECT 
                SUM(ingreso_reserva) as total_ingreso_reserva,
                SUM(ingreso_extras) as total_ingreso_extras,
                SUM(ingreso_total) as total_ingreso_total,
                SUM(costo_operativo_fijo) as total_costo_fijo,
                SUM(costo_operativo_variable) as total_costo_variable,
                SUM(costo_operativo_total) as total_costo_total,
                COUNT(*) as num_reservas
            FROM reservas_con_extras
            WHERE fecha = '2026-03-07'
        """
        
        totals = await db.execute_query(total_query)
        if totals:
            t = totals[0]
            print(f"\nNúmero de reservas: {t['num_reservas']}")
            print(f"\nIngresos:")
            print(f"  - Por Reservas: ${t['total_ingreso_reserva']:,.0f}")
            print(f"  - Por Extras: ${t['total_ingreso_extras']:,.0f}")
            print(f"  - TOTAL: ${t['total_ingreso_total']:,.0f}")
            print(f"\nCostos:")
            print(f"  - Fijos: ${t['total_costo_fijo']:,.0f}")
            print(f"  - Variables: ${t['total_costo_variable']:,.0f}")
            print(f"  - TOTAL: ${t['total_costo_total']:,.0f}")
            print(f"\nUtilidad: ${t['total_ingreso_total'] - t['total_costo_total']:,.0f}")
        
        # Ver también las tablas origen
        print(f"\n{'='*80}")
        print(f"DATOS ORIGEN - appointments (7 marzo)")
        print(f"{'='*80}\n")
        
        appt_query = """
            SELECT 
                id,
                customer_name,
                service_name,
                start_date,
                price
            FROM booknetic_appointments
            WHERE DATE(start_date) = '2026-03-07'
            ORDER BY start_date
        """
        
        appointments = await db.execute_query(appt_query)
        print(f"Total appointments: {len(appointments)}\n")
        
        for appt in appointments:
            print(f"ID {appt['id']}: {appt['customer_name']} - {appt['service_name']}")
            print(f"  Fecha: {appt['start_date']}, Precio: ${appt['price']:,.0f}")
        
        # Ver pagos
        print(f"\n{'='*80}")
        print(f"DATOS ORIGEN - payments (7 marzo)")
        print(f"{'='*80}\n")
        
        payment_query = """
            SELECT 
                id,
                appointment_id,
                created_date,
                total_amount,
                status
            FROM booknetic_payments
            WHERE appointment_id IN (
                SELECT id FROM booknetic_appointments WHERE DATE(start_date) = '2026-03-07'
            )
            ORDER BY appointment_id
        """
        
        payments = await db.execute_query(payment_query)
        print(f"Total payments: {len(payments)}\n")
        
        for payment in payments:
            print(f"Payment ID {payment['id']} - Appointment {payment['appointment_id']}")
            print(f"  Monto: ${payment['total_amount']:,.0f}, Estado: {payment['status']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_march_7())
