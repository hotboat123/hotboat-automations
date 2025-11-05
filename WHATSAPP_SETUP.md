# 📱 Configuración de WhatsApp Business API

Esta guía te ayudará a obtener las credenciales necesarias para enviar notificaciones a tu WhatsApp personal usando la WhatsApp Business API de Meta.

## 📋 Requisitos

- Una cuenta de Facebook
- Un número de teléfono que NO esté registrado en WhatsApp (para WhatsApp Business)
- Verificación de identidad en Meta Business

## 🚀 Pasos para obtener las credenciales

### 1. Crear una cuenta de Meta for Developers

1. Ve a [developers.facebook.com](https://developers.facebook.com/)
2. Inicia sesión con tu cuenta de Facebook
3. Haz clic en **"My Apps"** → **"Create App"**
4. Selecciona **"Business"** como tipo de aplicación
5. Completa el nombre de la app (ej: "HotBoat Notifications")

### 2. Configurar WhatsApp Business API

1. En el dashboard de tu app, busca **"WhatsApp"** en productos disponibles
2. Haz clic en **"Set Up"** junto a WhatsApp
3. Selecciona tu **Business Portfolio** o crea uno nuevo
4. Agrega un número de teléfono de prueba (Meta te proporciona uno temporal)

### 3. Obtener el Phone Number ID

1. En el panel de WhatsApp, ve a **"API Setup"**
2. Copia el **"Phone number ID"** (se ve algo así: `123456789012345`)
3. Este es tu `WHATSAPP_PHONE_NUMBER_ID`

### 4. Obtener el Access Token

**Opción A: Token temporal (para pruebas - 24 horas)**
1. En la sección "API Setup", verás un **"Temporary access token"**
2. Haz clic en **"Copy"** para copiarlo
3. Este token dura 24 horas, útil para pruebas

**Opción B: Token permanente (para producción)**
1. Ve a **"Business Settings"** → **"System Users"**
2. Crea un **System User** con permisos de administrador
3. Genera un token con los permisos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
4. Copia el token generado (¡guárdalo en lugar seguro!)

### 5. Agregar tu número personal como destinatario

1. En **"API Setup"**, verás una sección **"To"**
2. Agrega tu número personal de WhatsApp (formato: `+56912345678`)
3. WhatsApp te enviará un código de verificación
4. Ingresa el código para verificar tu número
5. Ahora tu número puede recibir mensajes del bot

### 6. Configurar las credenciales en el proyecto

Edita el archivo `.env` y agrega tus credenciales:

```bash
# WhatsApp Business API Configuration
WHATSAPP_ENABLED=true
WHATSAPP_API_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_RECIPIENTS=+56912345678
```

## 🧪 Probar la configuración

```bash
python test_config.py
```

O envía un mensaje de prueba:

```python
from app.notifications.whatsapp_notifier import WhatsAppNotifier
from app.config import settings
import asyncio

async def test():
    notifier = WhatsAppNotifier(settings)
    await notifier.initialize()
    await notifier.send("🎉 ¡WhatsApp funcionando correctamente!", priority="high")

asyncio.run(test())
```

## 📊 Límites de la API

### Cuenta de prueba (desarrollo):
- 1,000 mensajes gratuitos por mes
- Máximo 5 números de teléfono registrados
- Token temporal de 24 horas

### Cuenta verificada (producción):
- 1,000 conversaciones gratuitas por mes
- Conversaciones adicionales: $0.005 - $0.09 USD cada una
- Token permanente
- Números ilimitados

## 🔄 Pasar a producción

Para usar esto en producción:

1. **Verificar tu cuenta de negocios:**
   - Ve a Meta Business Suite
   - Completa la verificación de negocio
   - Proporciona documentos oficiales

2. **Agregar un número de teléfono propio:**
   - Necesitas un número que NO esté registrado en WhatsApp
   - Verifica el número siguiendo el proceso en Meta

3. **Generar token permanente:**
   - Usa System Users en Business Settings
   - El token no expira automáticamente

4. **Configurar un webhook (opcional):**
   - Para recibir respuestas de los usuarios
   - Necesitarás un servidor con HTTPS

## 🆘 Solución de problemas

### Error: "Invalid access token"
- Verifica que el token esté copiado correctamente
- Si es temporal, podría haber expirado (genera uno nuevo)

### Error: "Phone number not found"
- Verifica que el `WHATSAPP_PHONE_NUMBER_ID` sea correcto
- Asegúrate de estar usando el Phone Number ID, no el número de teléfono

### Error: "Recipient phone number not valid"
- El número debe estar en formato internacional: `+56912345678`
- No incluyas espacios ni guiones
- El número debe estar verificado en la plataforma de Meta

### No recibo mensajes
- Verifica que tu número esté agregado en "To" en API Setup
- Completa el código de verificación que WhatsApp te envió
- Revisa los logs en la plataforma de Meta

## 📚 Recursos adicionales

- [Documentación oficial de WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [Guía de inicio rápido](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Precios de WhatsApp Business](https://developers.facebook.com/docs/whatsapp/pricing)
- [Meta Business Help Center](https://www.facebook.com/business/help)

## 💡 Consejos

- Usa el token temporal para desarrollo y pruebas
- Genera un token permanente solo cuando vayas a producción
- Guarda tus tokens en un lugar seguro (nunca en el código)
- Considera usar variables de entorno o un gestor de secretos
- Monitorea el uso de tu API en el dashboard de Meta

---

¿Necesitas ayuda? Revisa los logs en `logs/automation.log` o contacta con soporte.

