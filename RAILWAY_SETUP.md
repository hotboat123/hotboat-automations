# 🚂 Despliegue en Railway

Esta guía te ayudará a desplegar **HotBoat Automations** en Railway con todas las variables de entorno configuradas.

## 📋 Variables de Entorno Configuradas

En Railway, tienes las siguientes variables configuradas:

### ✅ Base de Datos
- `DATABASE_URL` - URL de conexión a PostgreSQL (automática desde Railway)

### 📱 WhatsApp Business API
- `WHATSAPP_API_TOKEN` - Token de acceso de Meta
- `WHATSAPP_PHONE_NUMBER_ID` - ID del número de WhatsApp Business
- `WHATSAPP_BUSINESS_ACCOUNT_ID` - ID de la cuenta de negocios
- `WHATSAPP_VERIFY_TOKEN` - Token para verificación de webhooks

### 🔧 Configuración
- `PORT` - Puerto donde correrá la aplicación (Railway lo asigna automáticamente)

## 🚀 Despliegue Inicial

### 1. Conectar el Repositorio

```bash
# Ya tienes el repo en GitHub, ahora conéctalo a Railway:
# 1. Ve a railway.app
# 2. Click en "New Project"
# 3. Selecciona "Deploy from GitHub repo"
# 4. Busca: hotboat123/hotboat-automations
```

### 2. Agregar PostgreSQL

```bash
# En Railway:
# 1. Click en tu proyecto
# 2. Click en "New" → "Database" → "Add PostgreSQL"
# 3. Railway creará automáticamente DATABASE_URL
```

### 3. Configurar Variables de Entorno

En Railway, ve a tu servicio → **Variables** y agrega:

```bash
# WhatsApp (valores de tu consola de Meta)
WHATSAPP_ENABLED=true
WHATSAPP_API_TOKEN=tu_token_aqui
WHATSAPP_PHONE_NUMBER_ID=tu_phone_id_aqui
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_id_aqui
WHATSAPP_VERIFY_TOKEN=tu_verify_token_aqui
WHATSAPP_RECIPIENTS=+56912345678

# Configuración de monitores
CHECK_INTERVAL_APPOINTMENTS=60
CHECK_INTERVAL_STOCK=300
LOW_STOCK_THRESHOLD=5
CRITICAL_STOCK_THRESHOLD=2

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=production

# Email (opcional)
EMAIL_ENABLED=false

# Telegram (deshabilitado)
TELEGRAM_BOT_TOKEN=
```

### 4. Crear Procfile (para Railway)

Railway detectará automáticamente cómo ejecutar tu aplicación, pero puedes crear un `Procfile`:

```
worker: python main.py
```

### 5. Configurar el Start Command

En Railway → Settings → Deploy:
- **Start Command:** `python main.py`
- **Watch Paths:** (dejar por defecto)

## 🗄️ Configurar Base de Datos

Una vez desplegado, necesitas inicializar las tablas:

### Opción A: Desde Railway CLI

```bash
# Instala Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link a tu proyecto
railway link

# Ejecuta el script SQL
railway run python -c "
from app.database import init_db
import asyncio
asyncio.run(init_db())
"
```

### Opción B: Desde la Consola de Railway

1. Ve a tu base de datos PostgreSQL en Railway
2. Click en **"Data"** → **"Query"**
3. Pega el contenido de `setup_database.sql`
4. Ejecuta el script

## 📊 Verificar el Despliegue

### Ver Logs

```bash
# Desde Railway CLI
railway logs

# O desde el dashboard de Railway:
# Tu servicio → "Deployments" → Click en el deployment → "View Logs"
```

### Logs que deberías ver:

```
🚀 HotBoat Automations v1.0.0
📍 Entorno: production
🗄️  Base de datos conectada
💬 WhatsApp configurado para 1 destinatarios
✅ Monitor de Reservas iniciado (intervalo: 60s)
✅ Monitor de Stock iniciado (intervalo: 300s)
```

## 🔄 Despliegues Automáticos

Railway desplegará automáticamente cada vez que hagas push a tu rama principal:

```bash
# Haz cambios en tu código
git add .
git commit -m "Actualización"
git push origin main

# Railway detectará el push y desplegará automáticamente
```

## 🔒 Variables Sensibles

Las siguientes variables ya están configuradas en Railway y **NO** deben estar en tu código:

- ✅ `DATABASE_URL` - Railway la genera automáticamente
- ✅ `WHATSAPP_API_TOKEN` - Token de Meta
- ✅ `WHATSAPP_PHONE_NUMBER_ID` - ID de WhatsApp
- ✅ `PORT` - Railway lo asigna automáticamente

Estas variables están **protegidas** y no se subirán a GitHub gracias al `.gitignore`.

## 📱 Agregar Tu Número Personal

Tu número de WhatsApp debe estar registrado en la consola de Meta:

1. Ve a [developers.facebook.com](https://developers.facebook.com/)
2. Tu app → WhatsApp → API Setup
3. En la sección **"To"**, agrega tu número: `+56912345678`
4. WhatsApp te enviará un código de verificación
5. Ingresa el código
6. Actualiza la variable en Railway:
   ```
   WHATSAPP_RECIPIENTS=+56912345678
   ```

## 🧪 Probar desde Railway

```bash
# Conecta a Railway
railway link

# Ejecuta una prueba
railway run python test_config.py
```

## 🔍 Monitorear la Aplicación

### Health Check

Railway monitoreará automáticamente tu aplicación. Si falla, verás:
- ❌ Estado: "Crashed"
- 📋 Logs con el error

### Reiniciar Manualmente

```bash
# Desde Railway CLI
railway restart

# O desde el dashboard:
# Tu servicio → "..." → "Restart"
```

## 💰 Costos Estimados

### Railway:
- **Hobby Plan**: $5/mes
  - 500 horas de ejecución
  - $0.000231/min adicionales
- **PostgreSQL**: Incluido en Hobby Plan

### WhatsApp Business API:
- **Primeras 1,000 conversaciones**: Gratis
- **Conversaciones adicionales**: $0.005 - $0.09 USD c/u
- Una "conversación" dura 24 horas desde el primer mensaje

## 🆘 Solución de Problemas

### Error: "Application failed to respond"

```bash
# Verifica que main.py esté ejecutándose correctamente
railway logs --tail

# Asegúrate que el Start Command sea correcto:
# python main.py
```

### Error: "Database connection failed"

```bash
# Verifica que DATABASE_URL esté configurada
railway variables

# Debería mostrar: DATABASE_URL=postgresql://...
```

### Error: "WhatsApp token invalid"

1. Verifica en [developers.facebook.com](https://developers.facebook.com/)
2. Ve a tu app → WhatsApp → API Setup
3. Genera un nuevo token si el anterior expiró
4. Actualiza la variable en Railway:
   ```bash
   railway variables set WHATSAPP_API_TOKEN=nuevo_token
   ```

### No recibo notificaciones

1. Verifica los logs:
   ```bash
   railway logs --tail
   ```

2. Asegúrate que tu número esté verificado en Meta

3. Prueba manualmente:
   ```bash
   railway run python -c "
   from app.notifications.whatsapp_notifier import WhatsAppNotifier
   from app.config import Settings
   import asyncio
   
   async def test():
       settings = Settings()
       notifier = WhatsAppNotifier(settings)
       await notifier.initialize()
       await notifier.send('🧪 Prueba desde Railway', 'high')
   
   asyncio.run(test())
   "
   ```

## 📚 Comandos Útiles

```bash
# Ver variables de entorno
railway variables

# Agregar variable
railway variables set VARIABLE_NAME=value

# Ver logs en tiempo real
railway logs --tail

# Ejecutar comando en Railway
railway run python script.py

# Conectar a la base de datos
railway connect postgres

# Abrir dashboard
railway open
```

## 🔄 Actualizar Variables

Si necesitas cambiar alguna variable (ej: token de WhatsApp):

```bash
# Opción 1: Desde CLI
railway variables set WHATSAPP_API_TOKEN=nuevo_token

# Opción 2: Desde el Dashboard
# Railway → Tu servicio → Variables → Edit
```

Después de cambiar variables, Railway reiniciará automáticamente la aplicación.

## 📈 Escalar la Aplicación

Railway escala automáticamente según el uso. Para configuración avanzada:

1. Ve a Settings → Resources
2. Ajusta:
   - CPU
   - Memoria RAM
   - Número de instancias

## 🎉 ¡Listo!

Tu aplicación está corriendo 24/7 en Railway y enviará notificaciones a tu WhatsApp cada vez que:
- 📅 Haya una nueva reserva
- ❌ Se cancele una reserva
- ⚠️ El stock esté bajo
- 🚨 Un producto esté sin stock

---

¿Problemas? Revisa los logs: `railway logs --tail`

