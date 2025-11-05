# 🚀 Guía de Inicio Rápido - Railway

Esta guía te ayudará a desplegar HotBoat Automations en Railway en menos de 10 minutos.

## 🎯 Lo que necesitas

- ✅ Cuenta en [Railway](https://railway.app) (gratis)
- ✅ Cuenta en [Meta for Developers](https://developers.facebook.com) (gratis)
- ✅ Tu número de WhatsApp personal

---

## 📱 Paso 1: Configurar WhatsApp Business API (5 min)

### 1.1 Crear App en Meta for Developers

1. Ve a [developers.facebook.com](https://developers.facebook.com)
2. Click en **"My Apps"** → **"Create App"**
3. Selecciona **"Business"**
4. Nombre: `HotBoat Notifications`

### 1.2 Agregar WhatsApp

1. En el dashboard, busca **"WhatsApp"**
2. Click en **"Set Up"**
3. Selecciona o crea un Business Portfolio

### 1.3 Obtener Credenciales

Ve a **WhatsApp** → **API Setup** y copia:

```
✅ Phone number ID: 123456789012345
✅ Temporary access token: EAAxxxxxx...
✅ WhatsApp Business Account ID: 987654321
```

### 1.4 Agregar Tu Número Personal

1. En la sección **"To"**, agrega tu número: `+56912345678`
2. WhatsApp te enviará un código de verificación
3. Ingresa el código ✅

📚 **Guía detallada**: Ver `WHATSAPP_SETUP.md`

---

## 🚂 Paso 2: Desplegar en Railway (3 min)

### 2.1 Crear Proyecto

1. Ve a [railway.app](https://railway.app)
2. Click **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Busca: `hotboat123/hotboat-automations`

### 2.2 Agregar Base de Datos

1. Click en **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway creará automáticamente `DATABASE_URL` ✅

### 2.3 Configurar Variables de Entorno

En tu proyecto Railway, ve a **Variables** y agrega:

```bash
# WhatsApp (pega tus credenciales del Paso 1)
WHATSAPP_ENABLED=true
WHATSAPP_API_TOKEN=EAAxxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321
WHATSAPP_VERIFY_TOKEN=cualquier_string_secreto
WHATSAPP_RECIPIENTS=+56912345678

# Configuración de Monitores (¡TODO configurable desde aquí!)
CHECK_INTERVAL_APPOINTMENTS=60    # Segundos entre cada revisión de reservas
CHECK_INTERVAL_STOCK=300          # Segundos entre cada revisión de stock (5 min)
LOW_STOCK_THRESHOLD=5             # Alertar cuando quedan N unidades
CRITICAL_STOCK_THRESHOLD=2        # Alerta crítica cuando quedan N unidades

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=production
```

> 💡 **Ventaja de Railway**: Puedes cambiar cualquiera de estas variables sin modificar el código. Railway reiniciará automáticamente la aplicación con los nuevos valores.

> 🗄️ **¿Tus tablas tienen otros nombres?**
> - Ajusta `monitors.appointments.table_name` en `config.yaml` (por ejemplo `booknetic_appointments`).
> - O define `monitors.appointments.query` con la consulta exacta y alias a los campos esperados.
> - Haz lo mismo para `monitors.stock.table_name` o `monitors.stock.query`.
> - Revisa `CONFIGURATION.md` para ejemplos completos.

### 2.4 Desplegar

Railway desplegará automáticamente. Verás:
```
✅ Building...
✅ Deploying...
✅ Success!
```

---

## 📊 Paso 3: Inicializar Base de Datos (2 min)

### 3.1 Conectar a PostgreSQL de Railway

```bash
# Instala Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link a tu proyecto
railway link
```

### 3.2 Ejecutar Script SQL

Opción A - Desde Railway CLI:
```bash
railway run python -c "
from app.database import init_db
import asyncio
asyncio.run(init_db())
"
```

Opción B - Desde Railway Dashboard:
1. Ve a tu PostgreSQL → **Data** → **Query**
2. Pega el contenido de `setup_database.sql`
3. Click **Run**

---

## 🎉 ¡Listo! Verifica el Despliegue

### Ver Logs en Tiempo Real

Desde Railway CLI:
```bash
railway logs --tail
```

O desde el Dashboard:
- Tu servicio → **Deployments** → Click en el deployment → **View Logs**

### Logs que deberías ver:

```
🚀 HotBoat Automations v1.0.0
📍 Entorno: production
🗄️  Base de datos conectada
💬 WhatsApp configurado para 1 destinatarios
✅ Monitor de Reservas iniciado (intervalo: 60s)
✅ Monitor de Stock iniciado (intervalo: 300s)
```

### 📱 Mensaje de Inicio

Recibirás un mensaje en WhatsApp:
```
🚀 Sistema de automatizaciones iniciado correctamente
```

---

## 🧪 Probar el Sistema

### Probar Monitor de Stock

Conéctate a la base de datos de Railway:

```bash
railway connect postgres
```

Luego ejecuta:

```sql
-- Reducir stock a nivel bajo
UPDATE inventory 
SET quantity = 3 
WHERE product_name = 'Aceite Motor 2T';
```

**Resultado:** ⚠️ Recibirás WhatsApp sobre stock bajo

```sql
-- Stock crítico
UPDATE inventory 
SET quantity = 1 
WHERE product_name = 'Botiquín Primeros Auxilios';
```

**Resultado:** 🚨 WhatsApp de stock crítico

```sql
-- Sin stock
UPDATE inventory 
SET quantity = 0 
WHERE product_name = 'Botellas de Agua';
```

**Resultado:** 🚨 Alerta crítica por WhatsApp

### Probar Monitor de Appointments

```sql
-- Crear nueva reserva
INSERT INTO appointments (
    customer_name, phone_number, appointment_date, 
    start_time, boat_type, num_people, total_price
) VALUES (
    'Juan Pérez', '+56912345678', CURRENT_DATE + INTERVAL '1 day',
    '10:00', 'Lancha Deportiva', 4, 50000
);
```

**Resultado:** 📅 Notificación de nueva reserva en WhatsApp

---

## ⚙️ Configuración Avanzada (Railway)

### Ajustar Cualquier Variable

En Railway → **Variables**, puedes modificar en tiempo real:

#### Frecuencia de Monitoreo

```bash
CHECK_INTERVAL_APPOINTMENTS=30  # Revisar cada 30 segundos
CHECK_INTERVAL_STOCK=600        # Revisar cada 10 minutos (más espaciado)
```

#### Umbrales de Stock

```bash
LOW_STOCK_THRESHOLD=10      # Alertar cuando quedan 10 unidades
CRITICAL_STOCK_THRESHOLD=3  # Crítico en 3 unidades
```

Railway reiniciará automáticamente la app con los nuevos valores (tarda ~30 segundos).

> 🎯 **Prioridad de configuración**: Variables de entorno (Railway) > `config.yaml` > valores por defecto

### Ajustar Niveles de Prioridad

Edita `config.yaml` y haz commit:

```yaml
notifications:
  whatsapp:
    enabled: true
    priority_levels:
      critical: true  # Stock crítico, errores del sistema
      high: true      # Nuevas reservas, stock bajo
      medium: true    # Cambios en reservas
      low: false      # Info general (deshabilitado)
```

Railway desplegará automáticamente al hacer push.

---

## 🔄 Actualizar el Código

Cuando hagas cambios en el código:

```bash
git add .
git commit -m "Descripción de cambios"
git push origin main
```

Railway desplegará automáticamente en ~2 minutos.

---

## 🆘 Solución de Problemas

### Error: "Database connection failed"

```bash
# Verifica que DATABASE_URL esté configurada
railway variables

# Debe mostrar: DATABASE_URL=postgresql://...
```

### Error: "WhatsApp token invalid"

1. Ve a [developers.facebook.com](https://developers.facebook.com)
2. Tu app → WhatsApp → API Setup
3. Genera un nuevo token (si el temporal expiró)
4. Actualiza en Railway:

```bash
railway variables set WHATSAPP_API_TOKEN=nuevo_token
```

### No recibo mensajes en WhatsApp

**Verifica que tu número esté registrado:**
1. Ve a Meta for Developers → Tu app → WhatsApp → API Setup
2. En la sección **"To"**, debe aparecer tu número verificado ✅
3. Si no aparece, agrégalo y completa el código de verificación

**Verifica los logs:**
```bash
railway logs --tail
```

Busca líneas como:
```
❌ Error al enviar WhatsApp: 401 - Invalid token
💬 Mensaje WhatsApp enviado a +56912345678 ✅
```

### El servicio se crashea

Ver logs detallados:
```bash
railway logs --tail
```

Reiniciar manualmente:
```bash
railway restart
```

### Token de WhatsApp expiró (después de 24h)

El token temporal dura 24 horas. Para token permanente:

1. Ve a Meta Business Suite → Settings → System Users
2. Crea un System User
3. Genera token con permisos permanentes
4. Actualiza en Railway

Ver guía completa en `WHATSAPP_SETUP.md`

---

## 📊 Monitorear el Sistema

### Ver métricas en Railway

- **CPU Usage**: Railway → Tu servicio → **Metrics**
- **Memory**: Revisa el gráfico de RAM
- **Crashes**: Sección **Deployments** muestra fallos

### Health Check

Railway monitorea automáticamente tu app. Si falla:
- ❌ Estado cambia a "Crashed"
- 🔄 Railway intentará reiniciar (hasta 10 intentos)
- 📧 Recibirás email de notificación

---

## 💰 Costos

### Railway
- **Hobby Plan**: $5 USD/mes
  - 500 horas de ejecución
  - PostgreSQL incluido
  - $0.000231/min adicionales

### WhatsApp Business API
- **Primeras 1,000 conversaciones**: Gratis
- **Conversaciones adicionales**: ~$0.01 USD c/u
- Una "conversación" = 24 horas desde el primer mensaje

**Costo estimado mensual**: ~$5-10 USD (Railway + WhatsApp)

---

## 🚀 Próximos Pasos

- ✅ Agrega más monitores personalizados
- ✅ Configura webhooks de WhatsApp para recibir respuestas
- ✅ Agrega resúmenes diarios automáticos
- ✅ Integra con más sistemas (CRM, inventario, etc.)
- ✅ Crea dashboard web para visualización en tiempo real

---

## 📚 Documentación Adicional

- **Configuración de WhatsApp**: Ver `WHATSAPP_SETUP.md`
- **Despliegue completo en Railway**: Ver `RAILWAY_SETUP.md`
- **Ejemplos avanzados**: Ver `EXAMPLES.md`

---

¡Disfruta de tus automatizaciones 24/7! 🚤💬

