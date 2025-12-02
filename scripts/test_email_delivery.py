"""Script para verificar el envío de emails"""
import asyncio
import sys
from pathlib import Path

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


async def send_test_email(message: str):
    settings = get_settings()
    config = load_yaml_config()

    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()

    try:
        await notification_manager.send(
            message=f"🧪 Prueba Email HotBoat\n\n{message}",
            priority="high",
            channel="email"
        )
        logger.info("✅ Email de prueba enviado (verifica tu bandeja)")
    finally:
        await notification_manager.close()


if __name__ == "__main__":
    test_message = sys.argv[1] if len(sys.argv) > 1 else "Este es un email de verificación."
    asyncio.run(send_test_email(test_message))

