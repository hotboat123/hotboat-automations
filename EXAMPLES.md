# 📚 Ejemplos de Uso

## Escenarios Comunes

### 1. Nueva Reserva

**Situación:** Un cliente hace una nueva reserva

**SQL:**
```sql
INSERT INTO appointments (
    customer_name, 
    phone_number, 
    appointment_date, 
    start_time, 
    boat_type, 
    num_people, 
    total_price,
    status
) VALUES (
    'María González',
    '+56987654321',
    '2025-11-15',
    '14:00',
    'Lancha Rápida',
    6,
    80000,
    'confirmed'
);
```

**Notificación que recibes (WhatsApp/Email):**
```
🎉 Nueva Reserva HotBoat

👤 Cliente: María González
📞 Contacto: +56987654321
📅 Fecha: 15/11/2025 a las 14:00
🛥️ Servicio: Lancha Rápida
👥 Personas: 6
➕ Extras: Sin extras registradas
⏱️ Duración: N/A
💳 Pago: $80,000
👨‍✈️ Staff: Sin asignar
📌 Estado: confirmed
🆔 ID Reserva: 123
```

> 💡 **Nota**: Esta notificación se envía automáticamente tanto por **WhatsApp** (si está habilitado) 
> como por **Email** (si `EMAIL_ENABLED=true`). El email tiene el mismo contenido pero con formato HTML 
> profesional. No necesitas hacer nada adicional, el sistema detecta la nueva fila automáticamente.

---

### 2. Stock Bajo

**Situación:** Después de un tour, el combustible está bajo

**SQL:**
```sql
UPDATE inventory 
SET quantity = 4 
WHERE product_name = 'Aceite Motor 2T';
```

**Notificación:**
```
ℹ️ 🟡 Stock Bajo

📦 Producto: Aceite Motor 2T
📊 Cantidad actual: 4 litros
📌 Stock mínimo recomendado: 5
ℹ️ Considera reabastecer
```

---

### 3. Stock Crítico

**Situación:** Se usaron varios chalecos y queda poco

**SQL:**
```sql
UPDATE inventory 
SET quantity = 2 
WHERE product_name = 'Chalecos Salvavidas';
```

**Notificación:**
```
⚠️ 🟠 STOCK CRÍTICO

📦 Producto: Chalecos Salvavidas
🏷️ SKU: SAFE-001
📊 Cantidad actual: 2 unidades
⚠️ Por favor, reabastecer pronto
```

---

### 4. Sin Stock

**Situación:** Se acabaron las botellas de agua

**SQL:**
```sql
UPDATE inventory 
SET quantity = 0 
WHERE product_name = 'Botellas de Agua';
```

**Notificación:**
```
🚨 🔴 PRODUCTO SIN STOCK

📦 Producto: Botellas de Agua
🏷️ SKU: BEV-001
📂 Categoría: Bebidas
📊 Cantidad anterior: 8 unidades
⚠️ REQUIERE REPOSICIÓN URGENTE
```

---

### 5. Reserva Modificada

**Situación:** Un cliente cambia la hora de su reserva

**SQL:**
```sql
UPDATE appointments 
SET start_time = '16:00',
    num_people = 8
WHERE id = 1;
```

**Notificación:**
```
ℹ️ 🔄 Reserva Modificada

👤 Cliente: María González
📱 Teléfono: +56987654321

Cambios:
• Hora: 14:00 → 16:00
• Personas: 6 → 8
```

---

### 6. Reserva Cancelada

**Situación:** Un cliente cancela

**SQL:**
```sql
DELETE FROM appointments WHERE id = 1;
-- O cambiar el estado:
UPDATE appointments SET status = 'cancelled' WHERE id = 1;
```

**Notificación:**
```
ℹ️ ❌ Reserva Cancelada

👤 Cliente: María González
📅 Fecha: 15/11/2025
⏰ Hora: 14:00
```

---

### 7. Reposición de Stock

**Situación:** Llega una compra de suministros

**SQL:**
```sql
UPDATE inventory 
SET quantity = 50 
WHERE product_name = 'Botellas de Agua';
```

**Notificación:**
```
ℹ️ ✅ Stock Restaurado

📦 Producto: Botellas de Agua
📊 Cantidad: 0 → 50 unidades
👍 Stock restaurado a niveles normales
```

---

## Personalización de Monitores

### Crear un Monitor Personalizado

Ejemplo: Monitor de Mantenimiento de Embarcaciones

`app/monitors/maintenance_monitor.py`:
```python
from app.monitors.base_monitor import BaseMonitor
from datetime import datetime, timedelta

class MaintenanceMonitor(BaseMonitor):
    """Monitorea mantenimientos pendientes"""
    
    async def check(self):
        """Obtiene mantenimientos próximos"""
        query = """
            SELECT 
                boat_name,
                last_maintenance,
                next_maintenance_due,
                maintenance_type
            FROM boats
            WHERE next_maintenance_due <= CURRENT_DATE + INTERVAL '7 days'
        """
        
        results = await self.db.execute_query(query)
        return {str(i): boat for i, boat in enumerate(results)}
    
    async def detect_changes(self, current_state):
        """Notifica sobre mantenimientos próximos"""
        for boat in current_state.values():
            days_until = (boat['next_maintenance_due'] - datetime.now().date()).days
            
            if days_until <= 2:
                await self.send_notification(
                    f"🔧 URGENTE: Mantenimiento de {boat['boat_name']} "
                    f"vence en {days_until} días",
                    priority="high"
                )
```

Luego agregar en `config.yaml`:
```yaml
monitors:
  maintenance:
    enabled: true
    name: "Monitor de Mantenimiento"
    check_interval: 3600  # 1 hora
```

Y en `main.py`, agregar:
```python
from app.monitors.maintenance_monitor import MaintenanceMonitor

# En _initialize_monitors:
if monitors_config.get("maintenance", {}).get("enabled", False):
    maintenance_monitor = MaintenanceMonitor(
        settings=self.settings,
        config=monitors_config["maintenance"],
        notification_manager=self.notification_manager
    )
    self.monitors.append(maintenance_monitor)
```

---

## Integraciones

### Integrar con Sistema WhatsApp Existente

Puedes hacer que el sistema de WhatsApp cree appointments automáticamente:

En `hotboat-whatsapp/app/bot/conversation.py`:
```python
# Cuando se confirma una reserva:
import httpx

async def confirm_booking(self, booking_data):
    # Crear en la BD
    appointment_id = await self.db.create_appointment(booking_data)
    
    # El sistema de automatizaciones detectará este cambio
    # y enviará la notificación automáticamente
    
    return appointment_id
```

### Dashboard Web (Futuro)

Podrías crear un endpoint FastAPI para ver el estado:

`app/api.py`:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/status")
async def get_status():
    return {
        "monitors": [
            {"name": "Appointments", "status": "running", "last_check": "..."},
            {"name": "Stock", "status": "running", "last_check": "..."}
        ],
        "notifications_sent_today": 15,
        "alerts_active": 2
    }

@app.get("/stock")
async def get_stock():
    # Consultar inventario actual
    pass
```

---

## Scripts Útiles

### Generar Reporte Diario

`scripts/daily_report.py`:
```python
import asyncio
from app.database import DatabaseManager
from app.config import get_settings

async def generate_daily_report():
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    # Reservas del día
    appointments = await db.execute_query("""
        SELECT COUNT(*) as count, SUM(total_price) as total
        FROM appointments
        WHERE appointment_date = CURRENT_DATE
    """)
    
    # Stock crítico
    low_stock = await db.execute_query("""
        SELECT product_name, quantity
        FROM inventory
        WHERE quantity <= min_stock
        ORDER BY quantity
    """)
    
    # Generar reporte
    report = f"""
📊 REPORTE DIARIO - {datetime.now().strftime('%d/%m/%Y')}

📅 RESERVAS:
• Total: {appointments[0]['count']}
• Ingresos: ${appointments[0]['total']:,.0f}

📦 STOCK CRÍTICO:
{chr(10).join(f"• {item['product_name']}: {item['quantity']}" for item in low_stock)}
    """
    
    # Enviar por email o Telegram
    print(report)
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(generate_daily_report())
```

---

## Consejos y Mejores Prácticas

### 1. Ajustar Intervalos de Monitoreo

- **Appointments**: 30-60 segundos (cambios importantes en tiempo real)
- **Stock**: 5-10 minutos (no cambia tan rápido)
- **Mantenimiento**: 1 hora (no es urgente)

### 2. Prioridades de Notificaciones

**Critical (🚨):**
- Stock en 0
- Errores del sistema
- Mantenimiento vencido

**High (⚠️):**
- Nueva reserva
- Stock crítico
- Reserva cancelada

**Medium (ℹ️):**
- Reserva modificada
- Stock bajo
- Recordatorios

**Low (💬):**
- Stock restaurado
- Info general

### 3. Evitar Spam

Si recibes muchas notificaciones, ajusta en `config.yaml`:

```yaml
notifications:
  telegram:
    priority_levels:
      critical: true
      high: true
      medium: false  # Deshabilitar medium
      low: false
```

### 4. Logs

Los logs son tu amigo:
```bash
# Ver en tiempo real
tail -f logs/automation.log

# Buscar errores
grep ERROR logs/automation.log

# Últimas 100 líneas
tail -100 logs/automation.log
```

---

## 📧 Ejemplo de Email de Nueva Reserva

Cuando se agrega una nueva reserva en `booknetic_appointments`, recibes un email como este:

**Asunto:** `[IMPORTANTE] HotBoat Automations - 15/01/2026 18:45`

**Cuerpo (HTML con formato):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚤 HotBoat Automations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 Nueva Reserva HotBoat

👤 Cliente: Juan Pérez
📞 Contacto: +56912345678 | juan@example.com
📅 Fecha: 16/01/2026 a las 14:00
🛥️ Servicio: Lancha Deportiva - 8 personas
👥 Personas: 8
➕ Extras: 2 x Tabla de Quesos, 1 x Botella de Vino
⏱️ Duración: 4h
💳 Pago: $150,000
👨‍✈️ Staff: Carlos Rodríguez
📌 Estado: confirmed
🆔 ID Reserva: 12345
🕒 Creada: 15/01/2026 18:30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Este es un mensaje automático del sistema 
de monitoreo de HotBoat Chile.
Fecha: 15/01/2026 18:45:32
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Características del email:**

- ✅ **Formato HTML profesional** con colores según prioridad
- ✅ **Respuesta automática** - no necesitas hacer nada
- ✅ **Múltiples destinatarios** - configura varios emails en `EMAIL_TO`
- ✅ **Mismo contenido que WhatsApp** - consistencia en todas las notificaciones
- ✅ **Incluye toda la información** - cliente, fecha, extras, pagos, etc.

**Configuración para recibir estos emails:**

```bash
# En Railway Variables
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=notificaciones@hotboat.cl
SMTP_PASSWORD=tu_app_password
SMTP_USE_TLS=true
EMAIL_FROM=notificaciones@hotboat.cl
EMAIL_TO=admin@hotboat.cl,manager@hotboat.cl
```

Ver más detalles en: `CONFIGURATION.md` → Sección "📧 Configuración de Emails para Nuevas Reservas"

---

¿Necesitas más ejemplos? ¡Abre un issue en GitHub! 🚀

