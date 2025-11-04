"""
WhatsApp Notifier (usando WhatsApp Business API)
"""
import httpx
from typing import List

from app.logger import logger
from .base_notifier import BaseNotifier


class WhatsAppNotifier(BaseNotifier):
    """Envía notificaciones por WhatsApp Business API"""
    
    async def initialize(self):
        """Inicializa el notificador de WhatsApp"""
        if not self.settings.whatsapp_enabled:
            raise ValueError("WhatsApp no está habilitado")
        
        if not self.settings.whatsapp_api_token:
            raise ValueError("WHATSAPP_API_TOKEN no configurado")
        
        if not self.settings.whatsapp_phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID no configurado")
        
        self.recipients = self.settings.whatsapp_recipients_list
        if not self.recipients:
            raise ValueError("WHATSAPP_RECIPIENTS no configurado")
        
        self.api_url = f"https://graph.facebook.com/v18.0/{self.settings.whatsapp_phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.settings.whatsapp_api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"✅ WhatsApp configurado para {len(self.recipients)} destinatarios")
    
    async def send(self, message: str, priority: str = "medium"):
        """Envía un mensaje de WhatsApp"""
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
        
        # Enviar a todos los destinatarios
        async with httpx.AsyncClient() as client:
            for recipient in self.recipients:
                try:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": recipient,
                        "type": "text",
                        "text": {
                            "body": formatted_message
                        }
                    }
                    
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        logger.debug(f"💬 Mensaje WhatsApp enviado a {recipient}")
                    else:
                        logger.error(
                            f"❌ Error al enviar WhatsApp a {recipient}: "
                            f"{response.status_code} - {response.text}"
                        )
                
                except Exception as e:
                    logger.error(f"❌ Error al enviar WhatsApp a {recipient}: {e}")

