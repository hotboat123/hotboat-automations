"""
Base monitor class
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.logger import logger
from app.database import init_database, DatabaseManager


class BaseMonitor(ABC):
    """Clase base para todos los monitores"""
    
    def __init__(self, settings, config: Dict[str, Any], notification_manager):
        self.settings = settings
        self.config = config
        self.notification_manager = notification_manager
        self.db: Optional[DatabaseManager] = None
        self.running = False
        self.last_state: Optional[Any] = None
        
        # Prioridad: variables de entorno > config.yaml > default
        # Esto permite configurar desde Railway sin modificar archivos
        self.check_interval = config.get("check_interval", 60)
        self.name = config.get("name", self.__class__.__name__)
    
    async def initialize(self):
        """Inicializa el monitor"""
        self.db = await init_database()
        logger.info(f"🔧 {self.name} inicializado")
    
    @abstractmethod
    async def check(self) -> Any:
        """
        Revisa el estado actual (debe ser implementado por subclases)
        Retorna el estado actual para comparación
        """
        pass
    
    @abstractmethod
    async def detect_changes(self, current_state: Any) -> None:
        """
        Detecta cambios entre el estado anterior y el actual
        y envía notificaciones si es necesario
        """
        pass
    
    async def start(self):
        """Inicia el monitoreo"""
        self.running = True
        await self.initialize()
        
        logger.info(f"▶️ {self.name} iniciado (intervalo: {self.check_interval}s)")
        
        while self.running:
            try:
                # Realizar la verificación
                current_state = await self.check()
                
                # Detectar cambios
                if self.last_state is not None:
                    await self.detect_changes(current_state)
                elif current_state and getattr(
                    self, "process_first_cycle_when_state_nonempty", False
                ):
                    # P. ej. DailySummaryMonitor: si el proceso arranca justo después de las 9:00,
                    # la primera iteración debe poder enviar el reporte (antes se saltaba detect_changes).
                    await self.detect_changes(current_state)
                else:
                    logger.info(f"📸 {self.name}: Estado inicial capturado")
                
                # Actualizar estado
                self.last_state = current_state
                
            except Exception as e:
                logger.error(f"❌ Error en {self.name}: {e}", exc_info=True)
                await self.notification_manager.send(
                    message=f"❌ Error en {self.name}: {e}",
                    priority="high",
                    channel="telegram"
                )
            
            # Esperar hasta el próximo check
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Detiene el monitoreo"""
        self.running = False
        logger.info(f"⏹️ {self.name} detenido")
    
    async def send_notification(
        self,
        message: str,
        priority: str = "medium",
        channel: Optional[str] = None,
        attachments: Optional[List] = None
    ) -> bool:
        """Helper para enviar notificaciones"""
        return await self.notification_manager.send(
            message=message,
            priority=priority,
            channel=channel,
            attachments=attachments
        )

