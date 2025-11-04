"""
Base notifier class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseNotifier(ABC):
    """Clase base para todos los notificadores"""
    
    def __init__(self, settings, config: Dict[str, Any]):
        self.settings = settings
        self.config = config
        self.priority_levels = config.get("priority_levels", {
            "critical": True,
            "high": True,
            "medium": True,
            "low": False
        })
    
    @abstractmethod
    async def initialize(self):
        """Inicializa el notificador"""
        pass
    
    @abstractmethod
    async def send(self, message: str, priority: str = "medium"):
        """Envía una notificación"""
        pass
    
    async def close(self):
        """Cierra el notificador (si es necesario)"""
        pass
    
    def should_send(self, priority: str) -> bool:
        """Verifica si se debe enviar la notificación según la prioridad"""
        return self.priority_levels.get(priority, True)

