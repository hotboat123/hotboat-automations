"""
Script para cargar TODOS los datos históricos de reservas_con_extras 
a Reservas_Con_Extras_Sheets (one-time execution)
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

async def load_all_historical_data():
    """Carga TODOS los datos históricos sin restricción de fecha"""
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        # Obtener TODAS las reservas sin filtro de fecha
        query = """
            SELECT 
                id,
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
                extras_json,
                created_at,
                updated_at
            FROM reservas_con_extras
            ORDER BY fecha DESC, hora DESC
        """
        
        print("Consultando todas las reservas historicas...")
        reservas = await db.execute_query(query)
        
        print(f"Total de reservas encontradas: {len(reservas)}")
        
        if not reservas:
            print("No hay datos para sincronizar")
            return
        
        # Mostrar rango de fechas
        fechas = [r['fecha'] for r in reservas if r.get('fecha')]
        if fechas:
            print(f"Rango de fechas: {min(fechas)} a {max(fechas)}")
        
        # Insertar cada reserva
        success_count = 0
        error_count = 0
        
        for reserva in reservas:
            try:
                # Construir el objeto JSON para sheets
                sheets_data = {
                    'appointment_id': str(reserva.get('appointment_id') or ''),
                    'reservation_id': str(reserva.get('reservation_id') or ''),
                    'fecha': str(reserva.get('fecha') or ''),
                    'hora': str(reserva.get('hora') or ''),
                    'nombre_cliente': str(reserva.get('nombre_cliente') or ''),
                    'email': str(reserva.get('email') or ''),
                    'telefono': str(reserva.get('telefono') or ''),
                    'servicio': str(reserva.get('servicio') or ''),
                    'num_personas': int(reserva.get('num_personas') or 0),
                    'ingreso_reserva': float(reserva.get('ingreso_reserva') or 0),
                    'ingreso_extras': float(reserva.get('ingreso_extras') or 0),
                    'ingreso_total': float(reserva.get('ingreso_total') or 0),
                    'costo_operativo_fijo': float(reserva.get('costo_operativo_fijo') or 0),
                    'costo_operativo_variable': float(reserva.get('costo_operativo_variable') or 0),
                    'costo_operativo_total': float(reserva.get('costo_operativo_total') or 0),
                    'num_adultos': int(reserva.get('num_adultos') or 0),
                    'num_ninos': int(reserva.get('num_ninos') or 0),
                    'ciudad_origen': str(reserva.get('ciudad_origen') or ''),
                    'como_supieron': str(reserva.get('como_supieron') or ''),
                    'clima_del_dia': str(reserva.get('clima_del_dia') or ''),
                    'categoria_clientes': str(reserva.get('categoria_clientes') or ''),
                    'tipo_clientes': str(reserva.get('tipo_clientes') or ''),
                    'status': str(reserva.get('status') or ''),
                    'tiene_cruce': bool(reserva.get('tiene_cruce', False)),
                    'extras_json': reserva.get('extras_json') or {},
                }
                
                # Upsert en la tabla Sheets
                # Primero intentar update, si no existe hacer insert
                check_query = """
                    SELECT id FROM "Reservas_Con_Extras_Sheets"
                    WHERE raw->>'appointment_id' = %s AND raw->>'fecha' = %s
                """
                existing = await db.execute_query(check_query, (
                    str(reserva.get('appointment_id') or ''),
                    str(reserva.get('fecha') or '')
                ))
                
                if existing:
                    # Actualizar
                    update_query = """
                        UPDATE "Reservas_Con_Extras_Sheets"
                        SET raw = %s::jsonb, updated_at = NOW()
                        WHERE raw->>'appointment_id' = %s AND raw->>'fecha' = %s
                    """
                    await db.execute_non_query(update_query, (
                        json.dumps(sheets_data),
                        str(reserva.get('appointment_id') or ''),
                        str(reserva.get('fecha') or '')
                    ))
                else:
                    # Insertar
                    insert_query = """
                        INSERT INTO "Reservas_Con_Extras_Sheets" (raw, source, created_at, updated_at)
                        VALUES (%s::jsonb, 'reservas_con_extras', NOW(), NOW())
                    """
                    await db.execute_non_query(insert_query, (json.dumps(sheets_data),))
                
                success_count += 1
                
                if success_count % 10 == 0:
                    print(f"Procesadas {success_count} reservas...")
                
            except Exception as e:
                error_count += 1
                print(f"Error procesando reserva {reserva.get('appointment_id')}: {e}")
        
        print(f"\nSincronizacion completada:")
        print(f"- Exito: {success_count}")
        print(f"- Errores: {error_count}")
        
    except Exception as e:
        print(f"Error en la carga historica: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("CARGA DE DATOS HISTORICOS A RESERVAS_CON_EXTRAS_SHEETS")
    print("=" * 60)
    asyncio.run(load_all_historical_data())
