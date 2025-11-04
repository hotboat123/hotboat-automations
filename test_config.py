"""
Script de prueba para verificar la configuración del sistema
Ejecuta esto para asegurarte de que todo está configurado correctamente
"""
import asyncio
import sys
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")


async def test_config():
    """Prueba la configuración del sistema"""
    
    print("\n" + "="*60)
    print("🔍 VERIFICADOR DE CONFIGURACIÓN - HotBoat Automations")
    print("="*60 + "\n")
    
    all_ok = True
    
    # 1. Verificar archivo .env
    print_info("Verificando archivo .env...")
    if not Path(".env").exists():
        print_error("Archivo .env no encontrado")
        print_warning("Copia env.example a .env y configúralo")
        all_ok = False
    else:
        print_success("Archivo .env encontrado")
    
    # 2. Cargar configuración
    try:
        from app.config import get_settings, load_yaml_config
        settings = get_settings()
        config = load_yaml_config()
        print_success("Configuración cargada correctamente")
    except Exception as e:
        print_error(f"Error al cargar configuración: {e}")
        return False
    
    # 3. Verificar conexión a base de datos
    print_info("Verificando conexión a base de datos...")
    try:
        from app.database import DatabaseManager
        db = DatabaseManager(settings.database_url)
        await db.initialize()
        
        # Intentar una query simple
        result = await db.execute_single("SELECT version();")
        if result:
            version = list(result.values())[0]
            print_success(f"Conexión exitosa a PostgreSQL")
            print(f"   Version: {version[:50]}...")
        
        await db.close()
    except Exception as e:
        print_error(f"Error de conexión a BD: {e}")
        print_warning("Verifica DATABASE_URL en .env")
        all_ok = False
    
    # 4. Verificar tabla appointments
    print_info("Verificando tabla appointments...")
    try:
        db = DatabaseManager(settings.database_url)
        await db.initialize()
        result = await db.execute_query(
            "SELECT COUNT(*) as count FROM appointments;"
        )
        count = result[0]['count'] if result else 0
        print_success(f"Tabla appointments existe ({count} registros)")
        await db.close()
    except Exception as e:
        print_warning(f"Tabla appointments no encontrada o error: {e}")
        print_info("Si no tienes esta tabla, el monitor de appointments no funcionará")
        print_info("Puedes ejecutar setup_database.sql para crearla")
    
    # 5. Verificar tabla inventory
    print_info("Verificando tabla inventory...")
    try:
        db = DatabaseManager(settings.database_url)
        await db.initialize()
        result = await db.execute_query(
            "SELECT COUNT(*) as count FROM inventory;"
        )
        count = result[0]['count'] if result else 0
        print_success(f"Tabla inventory existe ({count} productos)")
        await db.close()
    except Exception as e:
        print_warning(f"Tabla inventory no encontrada: {e}")
        print_info("Ejecuta setup_database.sql para crear la tabla con datos de ejemplo")
    
    # 6. Verificar Telegram
    print_info("Verificando configuración de Telegram...")
    if settings.telegram_bot_token:
        print_success("TELEGRAM_BOT_TOKEN configurado")
        
        if settings.telegram_chat_ids_list:
            print_success(f"TELEGRAM_CHAT_IDS configurado ({len(settings.telegram_chat_ids_list)} chats)")
            
            # Intentar conectar con Telegram
            try:
                from telegram import Bot
                bot = Bot(token=settings.telegram_bot_token)
                bot_info = await bot.get_me()
                print_success(f"Bot de Telegram conectado: @{bot_info.username}")
                
                # Intentar enviar mensaje de prueba
                print_info("¿Quieres enviar un mensaje de prueba? (s/n): ", end='')
                response = input().lower()
                if response == 's':
                    for chat_id in settings.telegram_chat_ids_list:
                        try:
                            await bot.send_message(
                                chat_id=chat_id,
                                text="🧪 Mensaje de prueba del sistema de automatizaciones HotBoat"
                            )
                            print_success(f"Mensaje de prueba enviado al chat {chat_id}")
                        except Exception as e:
                            print_error(f"Error al enviar a chat {chat_id}: {e}")
                            print_warning("Asegúrate de haber iniciado conversación con el bot")
            except Exception as e:
                print_error(f"Error al conectar con Telegram: {e}")
                print_warning("Verifica que el token sea correcto")
                all_ok = False
        else:
            print_warning("TELEGRAM_CHAT_IDS no configurado")
            print_info("Agrega tu chat ID a .env (ver TELEGRAM_SETUP.md)")
    else:
        print_warning("Telegram no configurado")
        print_info("Ver TELEGRAM_SETUP.md para configurar")
    
    # 7. Verificar Email
    print_info("Verificando configuración de Email...")
    if settings.email_enabled:
        if settings.smtp_host and settings.smtp_username:
            print_success("Email SMTP configurado")
            if settings.email_to_list:
                print_success(f"Destinatarios: {len(settings.email_to_list)}")
            else:
                print_warning("EMAIL_TO no configurado")
        elif settings.sendgrid_api_key:
            print_success("Email SendGrid configurado")
        else:
            print_warning("Email habilitado pero sin configuración completa")
    else:
        print_info("Email deshabilitado")
    
    # 8. Verificar WhatsApp
    print_info("Verificando configuración de WhatsApp...")
    if settings.whatsapp_enabled:
        if settings.whatsapp_api_token and settings.whatsapp_phone_number_id:
            print_success("WhatsApp configurado")
            if settings.whatsapp_recipients_list:
                print_success(f"Destinatarios: {len(settings.whatsapp_recipients_list)}")
        else:
            print_warning("WhatsApp habilitado pero incompleto")
    else:
        print_info("WhatsApp deshabilitado")
    
    # 9. Verificar monitores
    print_info("Verificando configuración de monitores...")
    monitors_config = config.get("monitors", {})
    
    if monitors_config.get("appointments", {}).get("enabled"):
        print_success("Monitor de Appointments habilitado")
    else:
        print_info("Monitor de Appointments deshabilitado")
    
    if monitors_config.get("stock", {}).get("enabled"):
        print_success("Monitor de Stock habilitado")
    else:
        print_info("Monitor de Stock deshabilitado")
    
    # Resumen
    print("\n" + "="*60)
    if all_ok:
        print_success("✨ ¡Todo listo! Puedes ejecutar: python main.py")
    else:
        print_warning("Hay algunos problemas de configuración")
        print_info("Revisa los mensajes anteriores y corrige los errores")
    print("="*60 + "\n")
    
    return all_ok


if __name__ == "__main__":
    try:
        result = asyncio.run(test_config())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nPrueba cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

