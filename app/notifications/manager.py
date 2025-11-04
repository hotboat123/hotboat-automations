"""
Notification Manager - Coordina todos los canales de notificación
"""
from typing import Optional, Dict, Any
from app.logger import logger
from .telegram_notifier import TelegramNotifier
from .email_notifier import EmailNotifier
from .whatsapp_notifier import WhatsAppNotifier


class NotificationManager:
    """Gestiona todos los canales de notificación"""
    
    def __init__(self, settings, config: Dict[str, Any]):
        self.settings = settings
        self.config = config
        self.notifiers = {}
    
    async def initialize(self):
        """Inicializa todos los notificadores configurados"""
        notifications_config = self.config.get("notifications", {})
        
        # Telegram
        if notifications_config.get("telegram", {}).get("enabled", False):
            try:
                telegram = TelegramNotifier(
                    settings=self.settings,
                    config=notifications_config["telegram"]
                )
                await telegram.initialize()
                self.notifiers["telegram"] = telegram
                logger.info("📱 Notificador de Telegram activado")
            except Exception as e:
                logger.error(f"❌ Error al inicializar Telegram: {e}")
        
        # Email
        if notifications_config.get("email", {}).get("enabled", False):
            try:
                email = EmailNotifier(
                    settings=self.settings,
                    config=notifications_config["email"]
                )
                await email.initialize()
                self.notifiers["email"] = email
                logger.info("📧 Notificador de Email activado")
            except Exception as e:
                logger.error(f"❌ Error al inicializar Email: {e}")
        
        # WhatsApp
        if notifications_config.get("whatsapp", {}).get("enabled", False):
            try:
                whatsapp = WhatsAppNotifier(
                    settings=self.settings,
                    config=notifications_config["whatsapp"]
                )
                await whatsapp.initialize()
                self.notifiers["whatsapp"] = whatsapp
                logger.info("💬 Notificador de WhatsApp activado")
            except Exception as e:
                logger.error(f"❌ Error al inicializar WhatsApp: {e}")
        
        if not self.notifiers:
            logger.warning("⚠️ No hay notificadores configurados")
    
    async def send(
        self,
        message: str,
        priority: str = "medium",
        channel: Optional[str] = None
    ):
        """
        Envía una notificación a través de los canales configurados
        
        Args:
            message: Mensaje a enviar
            priority: Prioridad (critical, high, medium, low)
            channel: Canal específico o None para todos los configurados
        """
        if not self.notifiers:
            logger.warning(f"⚠️ No hay notificadores disponibles para: {message[:50]}...")
            return
        
        # Si se especificó un canal específico
        if channel:
            notifier = self.notifiers.get(channel)
            if notifier and notifier.should_send(priority):
                try:
                    await notifier.send(message, priority)
                except Exception as e:
                    logger.error(f"❌ Error al enviar por {channel}: {e}")
            return
        
        # Enviar por todos los canales configurados según prioridad
        for name, notifier in self.notifiers.items():
            if notifier.should_send(priority):
                try:
                    await notifier.send(message, priority)
                except Exception as e:
                    logger.error(f"❌ Error al enviar por {name}: {e}")
    
    async def close(self):
        """Cierra todos los notificadores"""
        for name, notifier in self.notifiers.items():
            try:
                await notifier.close()
                logger.info(f"🔌 {name} notificador cerrado")
            except Exception as e:
                logger.error(f"❌ Error al cerrar {name}: {e}")

