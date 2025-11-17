"""
HotBoat Automations - Sistema de monitoreo y notificaciones
"""
import asyncio
import signal
import sys
from pathlib import Path

from app.config import get_settings, load_yaml_config
from app.logger import setup_logger, logger
from app.monitors.appointments_monitor import AppointmentsMonitor
from app.monitors.stock_monitor import StockMonitor
from app.monitors.consumption_monitor import ConsumptionMonitor
from app.monitors.inventory_sync_monitor import InventorySyncMonitor
from app.notifications.manager import NotificationManager


class AutomationSystem:
    """Sistema principal de automatizaciones"""
    
    def __init__(self):
        self.settings = get_settings()
        self.config = load_yaml_config()
        self.logger = logger
        self.running = False
        self.monitors = []
        self.notification_manager = None
        
    async def initialize(self):
        """Inicializa el sistema"""
        self.logger.info("🚀 Iniciando HotBoat Automations...")
        
        # Crear directorio de logs si no existe
        Path("logs").mkdir(exist_ok=True)
        
        # Ejecutar migraciones de base de datos
        await self._run_migrations()
        
        # Inicializar sistema de notificaciones
        self.notification_manager = NotificationManager(
            settings=self.settings,
            config=self.config
        )
        await self.notification_manager.initialize()
        
        # Inicializar monitores
        await self._initialize_monitors()
        
        # Notificación de inicio
        if self.config.get("general", {}).get("startup_notification", True):
            await self.notification_manager.send(
                message="✅ Sistema de automatizaciones iniciado correctamente",
                priority="medium",
                channel="telegram"
            )
        
        self.logger.info(f"✅ Sistema inicializado con {len(self.monitors)} monitores activos")
    
    async def _run_migrations(self):
        """Ejecuta las migraciones de base de datos"""
        try:
            self.logger.info("🔄 Ejecutando migraciones de base de datos...")
            
            # Importar y ejecutar el script de migraciones
            from scripts.run_migrations import run_all_migrations
            
            # Ejecutar en un thread separado para no bloquear el loop
            import asyncio
            success = await asyncio.to_thread(run_all_migrations)
            
            if success:
                self.logger.info("✅ Migraciones completadas exitosamente")
            else:
                self.logger.warning("⚠️  Algunas migraciones no se completaron")
                
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando migraciones: {e}")
            # No fallar el inicio si las migraciones fallan
            self.logger.warning("⚠️  Continuando sin ejecutar migraciones...")
    
    async def _initialize_monitors(self):
        """Inicializa los monitores configurados"""
        monitors_config = self.config.get("monitors", {})
        
        # Monitor de Appointments
        if monitors_config.get("appointments", {}).get("enabled", False):
            appointments_monitor = AppointmentsMonitor(
                settings=self.settings,
                config=monitors_config["appointments"],
                notification_manager=self.notification_manager
            )
            self.monitors.append(appointments_monitor)
            self.logger.info("📅 Monitor de Appointments activado")
        
        # Monitor de Consumos (Info Reserva -> Inventario)
        if monitors_config.get("consumption", {}).get("enabled", False):
            consumption_monitor = ConsumptionMonitor(
                settings=self.settings,
                config=monitors_config["consumption"],
                notification_manager=self.notification_manager
            )
            self.monitors.append(consumption_monitor)
            self.logger.info("🧾 Monitor de Consumos activado")
        
        # Monitor de Stock
        if monitors_config.get("stock", {}).get("enabled", False):
            stock_monitor = StockMonitor(
                settings=self.settings,
                config=monitors_config["stock"],
                notification_manager=self.notification_manager
            )
            self.monitors.append(stock_monitor)
            self.logger.info("📦 Monitor de Stock activado")
        
        # Monitor de Sincronización Inventory → Google Sheets
        if monitors_config.get("inventory_sync", {}).get("enabled", False):
            inventory_sync_monitor = InventorySyncMonitor(
                settings=self.settings,
                config=monitors_config["inventory_sync"],
                notification_manager=self.notification_manager
            )
            self.monitors.append(inventory_sync_monitor)
            self.logger.info("🔄 Monitor de Sincronización Inventory → Sheets activado")
    
    async def start(self):
        """Inicia el sistema de monitoreo"""
        self.running = True
        
        # Iniciar todos los monitores en paralelo
        tasks = [monitor.start() for monitor in self.monitors]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("🛑 Deteniendo monitores...")
        except Exception as e:
            self.logger.error(f"❌ Error en el sistema: {e}", exc_info=True)
            await self.notification_manager.send(
                message=f"❌ Error crítico en el sistema: {e}",
                priority="critical",
                channel="telegram"
            )
    
    async def stop(self):
        """Detiene el sistema de monitoreo"""
        self.logger.info("🛑 Deteniendo HotBoat Automations...")
        self.running = False
        
        # Detener todos los monitores
        for monitor in self.monitors:
            await monitor.stop()
        
        # Cerrar sistema de notificaciones
        if self.notification_manager:
            await self.notification_manager.close()
        
        self.logger.info("✅ Sistema detenido correctamente")


async def main():
    """Función principal"""
    system = AutomationSystem()
    
    # Configurar manejo de señales para shutdown graceful
    def signal_handler(sig, frame):
        asyncio.create_task(system.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await system.initialize()
        await system.start()
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupción del usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        return 1
    finally:
        await system.stop()
    
    return 0


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass

    exit_code = asyncio.run(main())
    sys.exit(exit_code)

