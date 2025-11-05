# 🔧 Guía de Configuración

Esta guía explica cómo configurar HotBoat Automations usando variables de entorno (Railway) y archivos de configuración.

## 🎯 Prioridad de Configuración

El sistema sigue esta jerarquía:

```
Variables de Entorno (Railway) > config.yaml > Valores por Defecto
```

Esto significa que:
1. **Primero** busca en las variables de entorno de Railway
2. **Si no existe**, busca en `config.yaml`
3. **Si tampoco existe**, usa el valor por defecto

## 📊 Variables de Entorno (Railway)

### WhatsApp Business API

```bash
WHATSAPP_ENABLED=true
WHATSAPP_API_TOKEN=EAAxxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321
WHATSAPP_VERIFY_TOKEN=tu_verify_token
WHATSAPP_RECIPIENTS=+56912345678,+56987654321
```

### Base de Datos

```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

> 💡 Railway genera `DATABASE_URL` automáticamente cuando agregas PostgreSQL

### Configuración de Monitores

```bash
# Intervalos de revisión (en segundos)
CHECK_INTERVAL_APPOINTMENTS=60    # Cada 1 minuto
CHECK_INTERVAL_STOCK=300          # Cada 5 minutos

# Umbrales de stock
LOW_STOCK_THRESHOLD=5             # Stock bajo: 5 unidades
CRITICAL_STOCK_THRESHOLD=2        # Stock crítico: 2 unidades
```

### Logging

```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/automation.log
ENVIRONMENT=production            # production o development
```

### Puerto (Railway)

```bash
PORT=8080
```

> 💡 Railway asigna el puerto automáticamente

## 📄 Archivo config.yaml

El archivo `config.yaml` controla configuraciones más detalladas:

### Monitores

```yaml
monitors:
  appointments:
    enabled: true
    name: "Monitor de Reservas"
    check_interval: 60              # Sobreescrito por CHECK_INTERVAL_APPOINTMENTS
    table_name: "appointments"      # Cambia si tu tabla tiene otro nombre (ej: booknetic_appointments)
    # query: |                      # Opcional: query personalizada con ALIAS a los campos esperados
    #   SELECT
    #     id,
    #     full_name AS customer_name,
    #     phone AS phone_number,
    #     start_date::date AS appointment_date,
    #     start_date::time AS start_time,
    #     duration AS duration_hours,
    #     service AS boat_type,
    #     guests AS num_people,
    #     amount AS total_price,
    #     status,
    #     created_at,
    #     updated_at,
    #     notes
    #   FROM booknetic_appointments
    notifications:
      new_appointment: true
      cancelled_appointment: true
      modified_appointment: true
  
  stock:
    enabled: true
    name: "Monitor de Stock"
    check_interval: 300             # Sobreescrito por CHECK_INTERVAL_STOCK
    table_name: "inventory"
    # query: |                     # Opcional: query personalizada con ALIAS a los campos esperados
    #   SELECT
    #     id,
    #     product_name,
    #     sku,
    #     category,
    #     quantity,
    #     'unidades' AS unit,
    #     min_stock,
    #     updated_at AS last_updated
    #   FROM otro_inventario
    thresholds:
      low_stock: 5                  # Sobreescrito por LOW_STOCK_THRESHOLD
      critical_stock: 2             # Sobreescrito por CRITICAL_STOCK_THRESHOLD
      out_of_stock: 0
```

### Canales de Notificación

```yaml
notifications:
  whatsapp:
    enabled: true                   # Sobreescrito por WHATSAPP_ENABLED
    priority_levels:
      critical: true                # Enviar mensajes críticos
      high: true                    # Enviar mensajes importantes
      medium: true                  # Enviar mensajes normales
      low: false                    # No enviar mensajes de baja prioridad
  
  email:
    enabled: false
    priority_levels:
      critical: true
      high: true
      medium: false
      low: false
```

### Configuración General

```yaml
general:
  timezone: "America/Santiago"
  startup_notification: true        # Enviar mensaje al iniciar
  error_notification: true          # Enviar mensaje en caso de error
  health_check_interval: 3600       # Verificar salud cada hora
```

## 🚀 Ejemplos de Uso

### Ejemplo 1: Configuración Básica (Solo Railway)

Configura solo las variables de entorno en Railway:

```bash
DATABASE_URL=postgresql://...
WHATSAPP_ENABLED=true
WHATSAPP_API_TOKEN=xxx
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_RECIPIENTS=+56912345678
CHECK_INTERVAL_APPOINTMENTS=60
CHECK_INTERVAL_STOCK=300
LOW_STOCK_THRESHOLD=5
CRITICAL_STOCK_THRESHOLD=2
```

El sistema usará los valores por defecto del `config.yaml` para todo lo demás.

### Ejemplo 2: Configuración Mixta

**Variables de entorno** (Railway) - para valores que cambian frecuentemente:
```bash
CHECK_INTERVAL_APPOINTMENTS=30    # Revisar más seguido
LOW_STOCK_THRESHOLD=10            # Umbral más alto
```

**config.yaml** - para configuraciones más estables:
```yaml
notifications:
  whatsapp:
    priority_levels:
      critical: true
      high: true
      medium: false               # Desactivar mensajes medium
      low: false
```

### Ejemplo 3: Configuración para Desarrollo vs Producción

**Desarrollo** (local):
```bash
# .env
ENVIRONMENT=development
CHECK_INTERVAL_APPOINTMENTS=10    # Revisar cada 10 segundos (rápido)
CHECK_INTERVAL_STOCK=30           # Revisar cada 30 segundos
LOG_LEVEL=DEBUG                    # Logs detallados
```

**Producción** (Railway):
```bash
ENVIRONMENT=production
CHECK_INTERVAL_APPOINTMENTS=60    # Revisar cada minuto (normal)
CHECK_INTERVAL_STOCK=300          # Revisar cada 5 minutos
LOG_LEVEL=INFO                     # Logs normales
```

## 🔄 Cambiar Configuración en Railway

### Cambiar una variable

1. Ve a Railway → Tu proyecto → **Variables**
2. Click en la variable que quieres cambiar
3. Modifica el valor
4. Railway reiniciará automáticamente (~30 segundos)

### Agregar nueva variable

1. Railway → Variables → **New Variable**
2. Name: `CHECK_INTERVAL_APPOINTMENTS`
3. Value: `30`
4. Save

Railway reiniciará con la nueva configuración.

### Eliminar variable

1. Railway → Variables → Click en la variable
2. **Delete**
3. El sistema usará el valor de `config.yaml` o el default

## 📊 Variables Disponibles

| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | - | URL de conexión PostgreSQL |
| `WHATSAPP_ENABLED` | boolean | false | Habilitar WhatsApp |
| `WHATSAPP_API_TOKEN` | string | - | Token de Meta API |
| `WHATSAPP_PHONE_NUMBER_ID` | string | - | ID del número de WhatsApp |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | string | - | ID de cuenta de negocios |
| `WHATSAPP_VERIFY_TOKEN` | string | - | Token para webhooks |
| `WHATSAPP_RECIPIENTS` | string | - | Números separados por coma |
| `CHECK_INTERVAL_APPOINTMENTS` | int | 60 | Segundos entre revisiones |
| `CHECK_INTERVAL_STOCK` | int | 300 | Segundos entre revisiones |
| `LOW_STOCK_THRESHOLD` | int | 5 | Umbral de stock bajo |
| `CRITICAL_STOCK_THRESHOLD` | int | 2 | Umbral de stock crítico |
| `LOG_LEVEL` | string | INFO | Nivel de logging |
| `LOG_FILE` | string | logs/automation.log | Archivo de logs |
| `ENVIRONMENT` | string | development | Entorno de ejecución |
| `PORT` | int | 8080 | Puerto de la aplicación |

## 🎯 Mejores Prácticas

### ✅ Usar Variables de Entorno para:

- Credenciales (tokens, passwords)
- URLs de bases de datos
- Valores que cambian entre entornos (dev/prod)
- Configuración que necesitas cambiar frecuentemente

### ✅ Usar config.yaml para:

- Configuración de comportamiento (qué notificaciones enviar)
- Configuraciones complejas (múltiples niveles)
- Valores que raramente cambian
- Documentación del sistema

### ⚠️ Nunca:

- Guardar credenciales en `config.yaml` (usa variables de entorno)
- Hacer commit del archivo `.env` (está en `.gitignore`)
- Compartir tokens o passwords en el código

## 🔍 Ver Configuración Actual

Para ver qué configuración está usando tu app:

```bash
# En Railway CLI
railway logs --tail

# Busca líneas como:
# ✅ Monitor de Reservas iniciado (intervalo: 60s)
# ✅ Monitor de Stock iniciado (intervalo: 300s)
```

O agrega temporalmente en `main.py`:

```python
logger.info(f"Config: Appointments interval={settings.check_interval_appointments}")
logger.info(f"Config: Stock interval={settings.check_interval_stock}")
logger.info(f"Config: Low stock threshold={settings.low_stock_threshold}")
```

## 🆘 Solución de Problemas

### La variable no se aplica

1. Verifica que el nombre sea exactamente correcto (case-insensitive)
2. Revisa que Railway haya reiniciado después del cambio
3. Verifica los logs: `railway logs --tail`

### La app usa valor incorrecto

Recuerda la prioridad:
1. Variable de entorno (Railway)
2. config.yaml
3. Default

Si defines `CHECK_INTERVAL_APPOINTMENTS=30` en Railway y `check_interval: 60` en config.yaml, usará **30**.

---

¿Dudas? Revisa `QUICKSTART.md` o `RAILWAY_SETUP.md`

