# 🚀 Guía de Inicio Rápido

## 1. Instalación Rápida (5 minutos)

### Paso 1: Clonar y preparar
```bash
cd C:\Users\cuent\Desktop
cd hotboat-automations
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Paso 2: Configurar Base de Datos
1. Abre tu cliente PostgreSQL (pgAdmin, DBeaver, etc.)
2. Ejecuta el archivo `setup_database.sql`
3. Esto creará la tabla `inventory` con datos de ejemplo

### Paso 3: Crear Bot de Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía el comando `/newbot`
3. Sigue las instrucciones:
   - Nombre: `HotBoat Automations`
   - Username: `hotboat_automations_bot` (o el que prefieras)
4. **Guarda el token que te da** (ejemplo: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

5. Para obtener tu CHAT_ID:
   - Busca **@userinfobot** en Telegram
   - Envía `/start`
   - Te dará tu chat ID (ejemplo: `987654321`)

### Paso 4: Configurar Variables de Entorno

Copia el archivo de ejemplo:
```bash
copy env.example .env
```

Edita `.env` con tus datos:
```env
# Base de datos (copia del proyecto hotboat-whatsapp)
DATABASE_URL=postgresql://user:password@localhost:5432/hotboat

# Telegram (datos del paso anterior)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_IDS=987654321

# Email (opcional - Gmail)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
EMAIL_FROM=notificaciones@hotboat.cl
EMAIL_TO=admin@hotboat.cl

# WhatsApp (opcional - usa tus credenciales existentes)
WHATSAPP_ENABLED=false
```

### Paso 5: ¡Ejecutar!

```bash
python main.py
```

Deberías ver:
```
🚀 Iniciando HotBoat Automations...
✅ Pool de conexiones de BD inicializado
📱 Notificador de Telegram activado
📅 Monitor de Appointments activado
📦 Monitor de Stock activado
✅ Sistema inicializado con 2 monitores activos
```

Y recibirás un mensaje en Telegram: ✅ Sistema de automatizaciones iniciado correctamente

## 2. Probar el Sistema

### Probar Monitor de Stock

Abre tu cliente PostgreSQL y ejecuta:
```sql
-- Reducir stock a nivel bajo
UPDATE inventory 
SET quantity = 3 
WHERE product_name = 'Aceite Motor 2T';
```

**Resultado:** Recibirás una notificación en Telegram sobre stock bajo

```sql
-- Stock crítico
UPDATE inventory 
SET quantity = 1 
WHERE product_name = 'Botiquín Primeros Auxilios';
```

**Resultado:** Notificación de stock crítico

```sql
-- Sin stock
UPDATE inventory 
SET quantity = 0 
WHERE product_name = 'Botellas de Agua';
```

**Resultado:** Alerta crítica de producto sin stock

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

**Resultado:** Notificación de nueva reserva en Telegram

## 3. Configuración Avanzada

### Ajustar Frecuencia de Monitoreo

Edita `config.yaml`:
```yaml
monitors:
  appointments:
    check_interval: 30  # Revisar cada 30 segundos
  
  stock:
    check_interval: 600  # Revisar cada 10 minutos
```

### Ajustar Umbrales de Stock

```yaml
monitors:
  stock:
    thresholds:
      low_stock: 10      # Cambiar umbral a 10 unidades
      critical_stock: 3   # Crítico en 3
      out_of_stock: 0
```

### Habilitar Notificaciones por Email

En `.env`:
```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password_de_gmail
EMAIL_TO=admin@hotboat.cl,gerente@hotboat.cl
```

**Nota:** Para Gmail, necesitas crear una "Contraseña de Aplicación":
1. Ve a https://myaccount.google.com/security
2. Activa la verificación en 2 pasos
3. Ve a "Contraseñas de aplicaciones"
4. Genera una contraseña para "Correo"
5. Usa esa contraseña en `SMTP_PASSWORD`

En `config.yaml`:
```yaml
notifications:
  email:
    enabled: true
    priority_levels:
      critical: true
      high: true
```

## 4. Ejecutar como Servicio (Producción)

### Windows - Tarea Programada

1. Crea un archivo `start_automations.bat`:
```batch
@echo off
cd C:\Users\cuent\Desktop\hotboat-automations
call venv\Scripts\activate
python main.py
```

2. Abre "Programador de tareas" de Windows
3. Crear Tarea Básica > Nombre: "HotBoat Automations"
4. Desencadenador: "Al iniciar el sistema"
5. Acción: Ejecutar `start_automations.bat`

### Linux - systemd

Crea `/etc/systemd/system/hotboat-automations.service`:
```ini
[Unit]
Description=HotBoat Automations
After=network.target postgresql.service

[Service]
Type=simple
User=hotboat
WorkingDirectory=/home/hotboat/hotboat-automations
ExecStart=/home/hotboat/hotboat-automations/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable hotboat-automations
sudo systemctl start hotboat-automations
sudo systemctl status hotboat-automations
```

## 5. Solución de Problemas

### Error: "no se puede conectar a la base de datos"
- Verifica que PostgreSQL esté corriendo
- Verifica el `DATABASE_URL` en `.env`
- Prueba la conexión con: `psql "postgresql://user:password@localhost:5432/hotboat"`

### Error: "TELEGRAM_BOT_TOKEN no configurado"
- Verifica que creaste el archivo `.env`
- Verifica que el token no tenga espacios extras
- El token debe ser algo como: `123456789:ABCdefGHI...`

### No recibo notificaciones en Telegram
1. Verifica que iniciaste conversación con el bot (búscalo y dale `/start`)
2. Verifica que el `CHAT_ID` sea correcto
3. Revisa los logs en `logs/automation.log`

### Ver logs en tiempo real
```bash
# Windows PowerShell
Get-Content logs/automation.log -Wait -Tail 50

# Linux/Mac
tail -f logs/automation.log
```

## 6. Próximos Pasos

- ✅ Personaliza los mensajes en los monitores
- ✅ Agrega más monitores personalizados
- ✅ Configura resúmenes diarios por email
- ✅ Integra con tu sistema de WhatsApp existente
- ✅ Agrega dashboard web para visualización

¡Disfruta de tus automatizaciones! 🚤

