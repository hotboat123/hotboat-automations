"""
Telegram Notifier
"""
import asyncio
from typing import List
from telegram import Bot
from telegram.error import TelegramError

from app.logger import logger
from .base_notifier import BaseNotifier


class TelegramNotifier(BaseNotifier):
    """Envía notificaciones por Telegram"""
    
    async def initialize(self):
        """Inicializa el bot de Telegram"""
        if not self.settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN no configurado")
        
        self.bot = Bot(token=self.settings.telegram_bot_token)
        self.chat_ids = self.settings.telegram_chat_ids_list
        
        if not self.chat_ids:
            raise ValueError("TELEGRAM_CHAT_IDS no configurado")
        
        # Verificar conexión
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Bot de Telegram conectado: @{bot_info.username}")
        except TelegramError as e:
            logger.error(f"❌ Error al conectar con Telegram: {e}")
            raise
    
    async def send(self, message: str, priority: str = "medium"):
        """Envía un mensaje a todos los chats configurados"""
        if not self.should_send(priority):
            return
        
        # Agregar emoji según prioridad
        emoji_map = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "ℹ️",
            "low": "💬"
        }
        
        emoji = emoji_map.get(priority, "ℹ️")
        formatted_message = f"{emoji} {message}"
        
        # Enviar a todos los chat_ids
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message,
                    parse_mode="Markdown"
                )
                logger.debug(f"📱 Mensaje enviado a Telegram (chat_id: {chat_id})")
            except TelegramError as e:
                logger.error(f"❌ Error al enviar a Telegram (chat_id: {chat_id}): {e}")
    
    async def close(self):
        """Cierra la sesión del bot"""
        # El bot de python-telegram-bot no requiere cierre explícito
        pass

