"""
Script de prueba para verificar conexión a base de datos y WhatsApp
Ejecutar en Railway: railway run python test_connection.py
"""
import asyncio
import sys
from app.config import get_settings, load_yaml_config
from app.database import init_database
from app.notifications.whatsapp_notifier import WhatsAppNotifier
from app.logger import logger

async def test_database():
    """Prueba conexión a base de datos y cuenta reservas"""
    print("\n" + "="*60)
    print("🗄️  PROBANDO CONEXIÓN A BASE DE DATOS")
    print("="*60)
    
    try:
        db = await init_database()
        print("✅ Conexión a base de datos exitosa")
        
        # Contar reservas
        query = "SELECT COUNT(*) as total FROM appointments"
        result = await db.execute_query(query)
        
        if result and len(result) > 0:
            total = result[0]['total']
            print(f"✅ Total de reservas en appointments: {total}")
            return total
        else:
            print("⚠️  No se pudo obtener el conteo")
            return 0
            
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return None

async def test_whatsapp(message: str):
    """Prueba conexión a WhatsApp"""
    print("\n" + "="*60)
    print("📱 PROBANDO WHATSAPP")
    print("="*60)
    
    settings = get_settings()
    config = load_yaml_config()
    whatsapp_config = config.get("notifications", {}).get("whatsapp", {
        "priority_levels": {
            "critical": True,
            "high": True,
            "medium": True,
            "low": False,
        }
    })
    
    # Verificar configuración
    print(f"WHATSAPP_ENABLED: {settings.whatsapp_enabled}")
    print(f"WHATSAPP_API_TOKEN: {'✅ Configurado' if settings.whatsapp_api_token else '❌ NO configurado'}")
    print(f"WHATSAPP_PHONE_NUMBER_ID: {'✅ Configurado' if settings.whatsapp_phone_number_id else '❌ NO configurado'}")
    print(f"WHATSAPP_RECIPIENTS: {settings.whatsapp_recipients}")
    
    if not settings.whatsapp_enabled:
        print("❌ WhatsApp está deshabilitado (WHATSAPP_ENABLED=false)")
        return False
    
    if not settings.whatsapp_api_token or not settings.whatsapp_phone_number_id:
        print("❌ Faltan credenciales de WhatsApp")
        return False
    
    try:
        notifier = WhatsAppNotifier(settings, whatsapp_config)
        await notifier.initialize()
        print("✅ WhatsApp inicializado correctamente")
        
        # Enviar mensaje de prueba
        await notifier.send(message, priority="high")
        print("✅ Mensaje enviado a WhatsApp")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar WhatsApp: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Función principal"""
    print("\n" + "🚀 "*20)
    print("PRUEBA DE CONEXIÓN - HOTBOAT AUTOMATIONS")
    print("🚀 "*20 + "\n")
    
    # Prueba 1: Base de datos
    total_reservas = await test_database()
    
    if total_reservas is None:
        print("\n❌ FALLO: No se pudo conectar a la base de datos")
        print("\nVerifica en Railway:")
        print("  - Variable DATABASE_URL está configurada")
        print("  - PostgreSQL está corriendo")
        sys.exit(1)
    
    # Prueba 2: WhatsApp
    mensaje = f"""
🎉 **Prueba de Conexión Exitosa**

✅ Base de datos: Conectada
📊 Total de reservas: **{total_reservas}**

🚀 HotBoat Automations está funcionando correctamente!
"""
    
    whatsapp_ok = await test_whatsapp(mensaje.strip())
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    print(f"Base de datos: {'✅ OK' if total_reservas is not None else '❌ FALLO'}")
    print(f"WhatsApp: {'✅ OK' if whatsapp_ok else '❌ FALLO'}")
    print(f"Total reservas: {total_reservas}")
    print("="*60 + "\n")
    
    if not whatsapp_ok:
        print("\n⚠️  CONFIGURACIÓN REQUERIDA EN RAILWAY:")
        print("\nVe a Railway → Tu proyecto → Variables y agrega:")
        print("\nWHATSAPP_ENABLED=true")
        print("WHATSAPP_API_TOKEN=tu_token_de_meta")
        print("WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id")
        print("WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id")
        print("WHATSAPP_RECIPIENTS=+56912345678")
        print("\n📚 Ver guía completa en: WHATSAPP_SETUP.md\n")
        sys.exit(1)
    
    print("✅ TODAS LAS PRUEBAS PASARON\n")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

