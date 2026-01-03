"""
Script para probar el envío de email al agregar una nueva reserva
Este script simula la notificación que se envía cuando se detecta una nueva fila en appointments
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.logger import logger


def create_sample_appointment_message():
    """Crea un mensaje de ejemplo idéntico al que se envía con una nueva reserva"""
    message = """🎉 *Nueva Reserva HotBoat*

👤 Cliente: Juan Pérez (PRUEBA)
📞 Contacto: +56912345678 | juan@example.com
📅 Fecha: 16/01/2026 a las 14:00
🛥️ Servicio: Lancha Deportiva - 8 personas
👥 Personas: 8
➕ Extras: 2 x Tabla de Quesos, 1 x Botella de Vino
⏱️ Duración: 4h
💳 Pago: $150,000
👨‍✈️ Staff: Carlos Rodríguez
📌 Estado: confirmed
🆔 ID Reserva: TEST-12345
🕒 Creada: {created_at}

📝 Notas: Esta es una reserva de prueba para verificar el envío de emails.
""".format(created_at=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    return message


async def test_new_appointment_email():
    """Prueba el envío de email de nueva reserva"""
    settings = get_settings()
    config = load_yaml_config()
    
    if not settings.email_enabled:
        logger.error("❌ EMAIL_ENABLED=false - No se puede enviar email de prueba")
        logger.info("💡 Configura EMAIL_ENABLED=true en tus variables de entorno")
        return
    
    logger.info("📧 Preparando email de prueba de nueva reserva...")
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    message = create_sample_appointment_message()
    
    try:
        logger.info("📤 Enviando email de prueba...")
        await notification_manager.send(
            message=message,
            priority="high",
            channel="email"
        )
        logger.info("✅ Email de prueba enviado correctamente")
        logger.info("")
        logger.info("📬 Verifica tu bandeja de entrada en:")
        for email in settings.email_to_list:
            logger.info(f"   - {email}")
        logger.info("")
        logger.info("💡 Si no lo ves, revisa la carpeta de spam")
        logger.info("💡 El email debería tener el asunto: [IMPORTANTE] HotBoat Automations - ...")
        
    except Exception as e:
        logger.error(f"❌ Error al enviar email de prueba: {e}")
        logger.info("")
        logger.info("🔍 Posibles causas:")
        logger.info("   1. Verifica SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD")
        logger.info("   2. Si usas Gmail, asegúrate de usar una contraseña de aplicación")
        logger.info("   3. Verifica que EMAIL_TO esté configurado correctamente")
        logger.info("")
        logger.info("Ver más en: CONFIGURATION.md → Configuración de Emails para Nuevas Reservas")
        raise
    finally:
        await notification_manager.close()


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🧪 TEST: Email de Nueva Reserva")
    logger.info("="*60)
    logger.info("")
    
    asyncio.run(test_new_appointment_email())
    
    logger.info("")
    logger.info("="*60)
    logger.info("✅ Prueba completada")
    logger.info("="*60)

