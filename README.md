# HotBoat Automations

Sistema de monitoreo y notificaciones automáticas para Hot Boat Chile.

## 🚀 Características

- **Monitor de Appointments**: Detecta nuevas reservas y cambios en tiempo real
- **Notificaciones por Email**: Emails automáticos al agregar nuevas reservas
- **Monitor de Stock**: Alerta cuando el inventario está bajo
- **Notificaciones WhatsApp**: Mensajes instantáneos a tu teléfono personal
- **Reportes Diarios**: Resumen automático enviado cada mañana a las 9:00 AM
- **Configuración Flexible**: Ajusta umbrales y frecuencias de monitoreo
- **Logs Detallados**: Registro de todas las actividades
- **Desplegado en Railway**: Corre 24/7 en la nube

## 📋 Requisitos

- Python 3.8+
- PostgreSQL (Railway lo proporciona)
- WhatsApp Business API (Meta for Developers)
- Cuenta en Railway (para despliegue)

## 🔧 Instalación

### Opción A: Despliegue en Railway (Recomendado) 🚂

1. **Fork o clona este repositorio**

2. **Crea un proyecto en [Railway](https://railway.app)**
   - New Project → Deploy from GitHub
   - Selecciona: `hotboat123/hotboat-automations`

3. **Agrega PostgreSQL**
   - Click en "New" → Database → Add PostgreSQL
   - Railway creará automáticamente `DATABASE_URL`

4. **Configura las variables de entorno** (ver `RAILWAY_SETUP.md`)
   - `WHATSAPP_API_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_BUSINESS_ACCOUNT_ID`
   - `WHATSAPP_RECIPIENTS`

5. **¡Listo!** Railway desplegará automáticamente

👉 **Guía completa**: Ver `RAILWAY_SETUP.md`

### Opción B: Desarrollo Local 💻

1. Clona el repositorio:
```bash
git clone https://github.com/hotboat123/hotboat-automations.git
cd hotboat-automations
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:
```bash
cp env.example .env
# Edita .env con tus credenciales
```

5. Ejecuta el sistema:
```bash
python main.py
```

## 📊 Monitores Disponibles

### 1. Monitor de Appointments (Reservas)
Detecta:
- ✅ **Nuevas reservas creadas** → Envía email automáticamente con toda la información
- Reservas canceladas
- Cambios en reservas existentes
- Reservas próximas (recordatorio)

**Email Automático**: Cada vez que se agrega una nueva fila en `booknetic_appointments`, 
recibes un email detallado con: cliente, fecha, hora, servicio, personas, extras, pago, etc.

### 2. Monitor de Stock (Inventario)
Detecta:
- Productos con stock bajo
- Productos sin stock
- Cambios significativos en inventario

### 3. Monitor de Resumen Diario
Envía automáticamente:
- Reporte diario a las 9:00 AM (configurable)
- Comparación de reservas vs información completada
- Detalle de consumos registrados
- Lista de reservas sin información

## 🔔 Canales de Notificación

### WhatsApp (Principal)
- Notificaciones instantáneas de nuevas reservas
- Integración con WhatsApp Business API
- Mensajes a múltiples usuarios
- Ver guía: `WHATSAPP_SETUP.md`

### Email (Automático)
- ✅ **Email automático por cada nueva reserva**
- Reportes diarios a las 9:00 AM
- Alertas de stock crítico
- Formato HTML profesional
- Múltiples destinatarios
- Compatible con Gmail, SendGrid, Resend
- Ver guía: `CONFIGURATION.md` → Sección "Configuración de Emails"

### Telegram (Opcional)
- Notificaciones instantáneas
- Grupos o chats privados
- Formato rico con botones
- Ver guía: `TELEGRAM_SETUP.md`

## ⚙️ Configuración

### Configuración Rápida de Emails para Nuevas Reservas

Para recibir un email automáticamente cada vez que se agregue una nueva reserva:

**1. Variables de entorno (Railway):**
```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_contraseña_de_app  # Ver nota abajo
SMTP_USE_TLS=true
EMAIL_FROM=notificaciones@hotboat.cl
EMAIL_TO=admin@hotboat.cl,manager@hotboat.cl
```

**2. Gmail - Contraseña de Aplicación:**
- Ve a: https://myaccount.google.com/apppasswords
- Genera una nueva contraseña
- Úsala en `SMTP_PASSWORD`

**3. Verifica que funciona:**
```bash
# Ejecuta el script de prueba
python scripts/test_new_appointment_email.py
```

**4. ¡Listo!** Ahora recibirás un email cada vez que se agregue una nueva reserva.

### Personalización Avanzada

Edita `config.yaml` para personalizar:

```yaml
monitors:
  appointments:
    enabled: true
    check_interval: 60  # segundos
    notifications:
      new_appointment: true  # Enviar email por cada nueva reserva
  
  stock:
    enabled: true
    check_interval: 300  # segundos
    low_stock_threshold: 5
  
  daily_summary:
    enabled: true
    report_time: "09:00"  # Hora del reporte diario

notifications:
  email:
    enabled: true
    priority_levels:
      high: true  # Nuevas reservas y reportes diarios
  
  whatsapp:
    enabled: true
    priority_levels:
      high: true
```

Ver guía completa: `CONFIGURATION.md`

## 🔍 Logs

Los logs se guardan en `logs/automation.log` con rotación automática.

## 🛠️ Desarrollo

Para agregar un nuevo monitor:

1. Crea un archivo en `monitors/`
2. Hereda de `BaseMonitor`
3. Implementa `check()` y `detect_changes()`
4. Registra en `config.yaml`

## 📝 Licencia

MIT License - Hot Boat Chile

## 🤝 Soporte

Para problemas o sugerencias, abre un issue en GitHub.

