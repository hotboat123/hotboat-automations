"""
Script para cargar datos históricos a Reservas_Con_Extras_Sheets (formato columnar)
Lee de reservas_con_extras y llena la tabla de sheets
"""
import sys
import os
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from app.monitors.reservas_sheets_sync_monitor import ReservasSheetsSyncMonitor
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from dotenv import load_dotenv

load_dotenv()

async def load_all_historical_data():
    """Carga TODOS los datos históricos en Reservas_Con_Extras_Sheets"""
    
    print("\n" + "="*80)
    print("CARGANDO DATOS HISTÓRICOS A RESERVAS_CON_EXTRAS_SHEETS")
    print("="*80 + "\n")
    
    # Inicializar settings y config
    settings = get_settings()
    config = load_yaml_config()
    
    # Crear notification manager (aunque no lo usaremos)
    notification_manager = NotificationManager(settings, config)
    
    # Crear el monitor
    monitor_config = {
        "enabled": True,
        "check_interval": 600,
        "sync_from_today": False  # IMPORTANTE: sincronizar TODO el histórico
    }
    
    monitor = ReservasSheetsSyncMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    try:
        print("Consultando TODAS las reservas de reservas_con_extras...\n")
        
        # Obtener TODAS las reservas (sin filtro de fecha)
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
            ORDER BY fecha ASC
        """
        
        reservas = await monitor.db.execute_query(query)
        
        print(f"Total de reservas encontradas: {len(reservas)}\n")
        
        if not reservas:
            print("No hay datos para sincronizar")
            return
        
        # Mostrar rango de fechas
        fechas = [r['fecha'] for r in reservas if r.get('fecha')]
        if fechas:
            print(f"Rango de fechas: {min(fechas)} a {max(fechas)}\n")
        
        # Sincronizar usando el método del monitor
        print("Sincronizando a Reservas_Con_Extras_Sheets...\n")
        
        success = 0
        errors = 0
        
        for i, reserva in enumerate(reservas, 1):
            try:
                await monitor._upsert_reserva_to_sheets(reserva)
                success += 1
                
                if i % 50 == 0:
                    print(f"Procesadas: {i}/{len(reservas)}")
                    
            except Exception as e:
                errors += 1
                print(f"Error en reserva {reserva.get('appointment_id')}: {e}")
        
        print(f"\n{'='*80}")
        print("SINCRONIZACIÓN COMPLETADA")
        print(f"{'='*80}\n")
        print(f"Éxitos: {success}")
        print(f"Errores: {errors}")
        print(f"Total procesados: {len(reservas)}\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await monitor.db.close()

if __name__ == "__main__":
    asyncio.run(load_all_historical_data())
