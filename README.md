# HotBoat Automations

Sistema de monitoreo y notificaciones automáticas para Hot Boat Chile.

## 🚀 Características

- **Monitor de Appointments**: Detecta nuevas reservas y cambios en tiempo real
- **Monitor de Stock**: Alerta cuando el inventario está bajo
- **Notificaciones Múltiples**: Telegram, Email, WhatsApp
- **Configuración Flexible**: Ajusta umbrales y frecuencias de monitoreo
- **Logs Detallados**: Registro de todas las actividades

## 📋 Requisitos

- Python 3.8+
- PostgreSQL (base de datos de HotBoat)
- Cuenta de Telegram Bot (para notificaciones)
- SMTP o SendGrid (para emails)

## 🔧 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/tuusuario/hotboat-automations.git
cd hotboat-automations
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita .env con tus credenciales
```

5. Ejecuta el sistema:
```bash
python main.py
```

## 📊 Monitores Disponibles

### 1. Monitor de Appointments (Reservas)
Detecta:
- Nuevas reservas creadas
- Reservas canceladas
- Cambios en reservas existentes
- Reservas próximas (recordatorio)

### 2. Monitor de Stock (Inventario)
Detecta:
- Productos con stock bajo
- Productos sin stock
- Cambios significativos en inventario

## 🔔 Canales de Notificación

### Telegram
- Notificaciones instantáneas
- Grupos o chats privados
- Formato rico con botones

### Email
- Resúmenes diarios/horarios
- Alertas críticas
- Formato HTML profesional

### WhatsApp (Opcional)
- Integración con WhatsApp Business API
- Notificaciones a múltiples usuarios

## ⚙️ Configuración

Edita `config.yaml` para personalizar:

```yaml
monitors:
  appointments:
    enabled: true
    check_interval: 60  # segundos
  
  stock:
    enabled: true
    check_interval: 300  # segundos
    low_stock_threshold: 5

notifications:
  telegram:
    enabled: true
    chat_ids: [123456789]
  
  email:
    enabled: true
    recipients: ["admin@hotboat.cl"]
```

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

