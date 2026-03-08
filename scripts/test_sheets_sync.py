"""
Script para probar el monitor de sincronización de reservas a Google Sheets
"""
import asyncio
import sys
from pathlib import Path

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.monitors.reservas_sheets_sync_monitor import ReservasSheetsSyncMonitor


async def test_sync():
    """Prueba el monitor de sincronización"""
    print("\n" + "="*80)
    print("PRUEBA DE SINCRONIZACION RESERVAS -> GOOGLE SHEETS")
    print("="*80 + "\n")
    
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = ReservasSheetsSyncMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("reservas_sheets_sync", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    print("\n[INFO] Obteniendo datos de reservas_con_extras...")
    current_state = await monitor.check()
    print(f"[INFO] Registros obtenidos: {len(current_state)}")
    
    if current_state:
        print(f"[INFO] Primera reserva: {current_state[0].get('fecha')} - {current_state[0].get('nombre_cliente')}")
        print(f"[INFO] Última reserva: {current_state[-1].get('fecha')} - {current_state[-1].get('nombre_cliente')}")
    
    print("\n[INFO] Iniciando sincronización...")
    await monitor.detect_changes(current_state)
    
    await notification_manager.close()
    
    print("\n[OK] Prueba completada!")
    print("\nVerifica la tabla Reservas_Con_Extras_Sheets en Railway\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_sync())
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
