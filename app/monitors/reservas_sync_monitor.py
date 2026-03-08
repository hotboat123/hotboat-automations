"""
Monitor de Sincronización de Reservas con Extras
Mantiene actualizada la tabla materializada reservas_con_extras
"""
from typing import Dict, Any
from datetime import datetime, timedelta, date
import asyncio
import subprocess

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class ReservasSyncMonitor(BaseMonitor):
    """Sincroniza la tabla reservas_con_extras automáticamente"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 600)  # 10 minutos por defecto
        self.lookback_days = config.get("lookback_days", 7)  # Sincronizar últimos 7 días
        self.last_sync_date = None
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info(
            f"🔄 Monitor de Sincronización de Reservas inicializado "
            f"(intervalo: {self.check_interval}s, lookback: {self.lookback_days} días)"
        )
        
        # Sincronización inicial
        logger.info("🔄 Ejecutando sincronización inicial...")
        await self._sync_now()
    
    async def check(self) -> Dict[str, Any]:
        """
        Chequea si es momento de sincronizar
        Retorna datos para el proceso de sincronización
        """
        current_date = date.today()
        
        # Sincronizar si no se ha hecho hoy
        if self.last_sync_date != current_date:
            return {"sync_needed": True, "date": current_date}
        
        return {}
    
    async def detect_changes(self, current_state: Dict[str, Any]) -> None:
        """
        Ejecuta la sincronización si es necesario
        """
        if not current_state or not current_state.get("sync_needed"):
            return
        
        logger.info("🔄 Iniciando sincronización de reservas_con_extras...")
        
        try:
            await self._sync_now()
            self.last_sync_date = current_state.get("date")
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}", exc_info=True)
            
            # Notificar error crítico
            await self.send_notification(
                message=f"❌ Error sincronizando reservas_con_extras: {e}",
                priority="critical",
                channel=None
            )
    
    async def _sync_now(self):
        """Ejecuta el script de sincronización"""
        # Calcular rango de fechas
        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Sincronizando periodo: {start_str} a {end_str}")
        
        # Ejecutar script de sincronización
        def run_sync():
            import sys
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "sync_reservas_con_extras.py"
            
            result = subprocess.run(
                [sys.executable, str(script_path), start_str, end_str],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            return result
        
        # Ejecutar en thread separado para no bloquear
        result = await asyncio.to_thread(run_sync)
        
        if result.returncode == 0:
            logger.info("✅ Sincronización completada exitosamente")
            
            # Parsear resultado para extraer estadísticas
            output = result.stdout
            if "Insertados:" in output:
                logger.info(f"📊 {output.split('Insertados:')[1].split('Actualizados:')[0].strip()} nuevos registros")
            if "Actualizados:" in output:
                logger.info(f"📊 {output.split('Actualizados:')[1].split('Total')[0].strip()} registros actualizados")
        else:
            error_msg = result.stderr or result.stdout
            logger.error(f"❌ Error en sincronización: {error_msg}")
            raise Exception(f"Script de sincronización falló: {error_msg}")
