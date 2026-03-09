"""
Script para sincronizar TODOS los datos históricos de reservas_con_extras 
a Reservas_Con_Extras_Sheets
Ejecutar en Railway con: railway run python scripts/sync_all_historical_data.py
"""
import sys
import os
import json
from datetime import datetime
import asyncio

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def sync_all_data():
    """Sincroniza todos los datos históricos"""
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    
    try:
        await db.initialize()
        print("Conexion a BD establecida")
        
        # Query para obtener todas las reservas
        query = """
            SELECT 
                appointment_id,
                reservation_id,
                fecha,
                hora,
                nombre_cliente,
                email,
                telefono,
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
                ciudad_origen,
                como_supieron,
                clima_del_dia,
                categoria_clientes,
                tipo_clientes,
                status,
                tiene_cruce,
                extras_json
            FROM reservas_con_extras
            ORDER BY fecha DESC, hora DESC
        """
        
        print("Consultando reservas...")
        reservas = await db.execute_query(query)
        print(f"Total reservas: {len(reservas)}")
        
        success = 0
        errors = 0
        
        for i, r in enumerate(reservas, 1):
            try:
                # Construir JSON
                data = {
                    'appointment_id': str(r.get('appointment_id') or ''),
                    'reservation_id': str(r.get('reservation_id') or ''),
                    'fecha': str(r.get('fecha') or ''),
                    'hora': str(r.get('hora') or ''),
                    'nombre_cliente': str(r.get('nombre_cliente') or ''),
                    'email': str(r.get('email') or ''),
                    'telefono': str(r.get('telefono') or ''),
                    'servicio': str(r.get('servicio') or ''),
                    'num_personas': int(r.get('num_personas') or 0),
                    'ingreso_reserva': float(r.get('ingreso_reserva') or 0),
                    'ingreso_extras': float(r.get('ingreso_extras') or 0),
                    'ingreso_total': float(r.get('ingreso_total') or 0),
                    'costo_operativo_fijo': float(r.get('costo_operativo_fijo') or 0),
                    'costo_operativo_variable': float(r.get('costo_operativo_variable') or 0),
                    'costo_operativo_total': float(r.get('costo_operativo_total') or 0),
                    'num_adultos': int(r.get('num_adultos') or 0),
                    'num_ninos': int(r.get('num_ninos') or 0),
                    'ciudad_origen': str(r.get('ciudad_origen') or ''),
                    'como_supieron': str(r.get('como_supieron') or ''),
                    'clima_del_dia': str(r.get('clima_del_dia') or ''),
                    'categoria_clientes': str(r.get('categoria_clientes') or ''),
                    'tipo_clientes': str(r.get('tipo_clientes') or ''),
                    'status': str(r.get('status') or ''),
                    'tiene_cruce': bool(r.get('tiene_cruce', False)),
                    'extras_json': r.get('extras_json') or {},
                }
                
                # Check si existe
                check = await db.execute_query(
                    'SELECT id FROM "Reservas_Con_Extras_Sheets" WHERE raw->>\'appointment_id\' = %s AND raw->>\'fecha\' = %s',
                    (data['appointment_id'], data['fecha'])
                )
                
                if check:
                    # Update
                    await db.execute_non_query(
                        'UPDATE "Reservas_Con_Extras_Sheets" SET raw = %s::jsonb, updated_at = NOW() WHERE raw->>\'appointment_id\' = %s AND raw->>\'fecha\' = %s',
                        (json.dumps(data), data['appointment_id'], data['fecha'])
                    )
                else:
                    # Insert
                    await db.execute_non_query(
                        'INSERT INTO "Reservas_Con_Extras_Sheets" (raw, source, created_at, updated_at) VALUES (%s::jsonb, \'reservas_con_extras\', NOW(), NOW())',
                        (json.dumps(data),)
                    )
                
                success += 1
                if i % 50 == 0:
                    print(f"Procesadas: {i}/{len(reservas)}")
                    
            except Exception as e:
                errors += 1
                print(f"Error en reserva {r.get('appointment_id')}: {e}")
        
        print(f"\nCompletado: {success} exitos, {errors} errores")
        
    except Exception as e:
        print(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(sync_all_data())
