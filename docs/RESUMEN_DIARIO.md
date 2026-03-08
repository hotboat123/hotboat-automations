# 📊 Monitor de Resumen Diario - Guía Completa

Explicación detallada de cómo funciona el reporte diario automático que se envía cada mañana.

## 🎯 ¿Qué Es el Resumen Diario?

Es un email que se envía **automáticamente cada mañana a las 09:00 AM** (hora Chile) con el resumen completo del día anterior, incluyendo:

- ✅ Reservas vs información completada
- 💰 Ingresos del día (reservas + extras)
- 💸 Costos (marketing + operativos)
- 📈 Utilidad neta y márgenes
- ⚠️ Reservas sin completar
- 🧾 Detalle de consumos registrados

---

## ⏰ ¿Cuándo se Envía?

### Configuración en `config.yaml`:

```yaml
daily_summary:
  enabled: true
  name: "Monitor de Resumen Diario"
  check_interval: 300  # chequea cada 5 minutos si es hora
  report_time: "09:00"  # hora de envío (24h)
  timezone: "America/Santiago"  # zona horaria
```

**Funcionamiento:**
1. El monitor chequea cada **5 minutos** si es hora de enviar
2. Cuando detecta que es **09:00 AM o más tarde**, genera el reporte
3. Solo envía **un reporte por día**
4. El reporte contiene datos del **día anterior**

---

## 📧 Estructura del Email

### 1. **Encabezado - Estado General**

```
✅ REPORTE DIARIO - 07/03/2026

📅 Reservas del día: 5
📝 Información completada: 5
✅ Faltantes: 0

Estado: TODAS COMPLETAS
```

**Estados posibles:**
- ✅ `TODAS COMPLETAS` - Todas las reservas tienen información completada
- ⚠️ `ALGUNAS FALTANTES` - Menos de 50% sin completar
- 🔴 `MUCHAS FALTANTES` - Más de 50% sin completar

### 2. **Sección de Ingresos**

```
========================================
💰 INGRESOS DEL DÍA

💵 Total Reservas: $957,810
🍾 Total Extras: $50,000
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: $1,007,810

📊 Promedio por reserva: $201,562
🧾 Pagos registrados: 5
```

**Cálculo de ingresos de reservas:**
- Usa el campo `payment` de `booknetic_appointments`
- Es el precio **ya descontado** (precio final que pagó el cliente)
- **NO** usa tabla de precios base

**Cálculo de ingresos de extras:**
- Lee los extras desde `Informacion Reservas` (tabla del formulario)
- Busca campos que empiecen con: `extras`, `cervezas`, `tablas`, `bebidas_y_jugos`, `otros_alcoholes`, `cha`
- Obtiene precios desde la tabla `Precios Extras` (columna `Precio`)
- Usa sistema de **aliases inteligentes** para mapear variantes de nombres

### 3. **Sección de Costos**

```
========================================
💸 COSTOS DEL DÍA

📢 Marketing: $5,000 (2 anuncios)

🏭 Costos Operativos: $118,000
   Fijos (5 reservas × $18,000):
     • Gas: $75,000
     • Leña: $5,000
     • Agua: $5,000
     • Hielo: $5,000
   
   Variables (extras desde BD):
     • Videos: $10,000
     • Tablas: $12,000
     • Marcos: $2,000
     • Otros: $4,000
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: $123,000
```

**Costos Fijos (por reserva):**
- Gas: $15,000
- Leña: $1,000
- Agua: $1,000
- Hielo: $1,000
- **Total fijo: $18,000 por reserva**

**Costos Variables:**
- Lee los mismos extras que para ingresos
- Obtiene costos desde tabla `Precios Extras` (columna `costo`)
- Usa el mismo sistema de aliases inteligentes
- Los clasifica en: Videos, Tablas, Marcos, Otros

**Costos de Marketing:**
- Lee desde tabla `marketing_costs`
- Filtra por fecha (`cost_date = fecha_ayer`)
- Suma todos los `amount_spent` del día

### 4. **Sección de Utilidad Neta**

```
========================================
📈 UTILIDAD NETA

💰 Ingresos: $1,007,810
💸 Costos Totales: -$123,000
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD NETA: $884,810
📊 Margen Neto: 87.8%
```

**Fórmulas:**
- **Ingresos Totales** = Reservas + Extras
- **Costos Totales** = Marketing + Operativos (Fijos + Variables)
- **Utilidad Neta** = Ingresos - Costos Totales
- **Margen Neto** = (Utilidad Neta / Ingresos) × 100

### 5. **Detalle por Reserva**

```
DETALLE POR RESERVA:

1. 09:00 - javier figueroa
   👥 5 personas
   💵 Subtotal Reserva: $194,950
   💰 Total: $194,950

2. 11:00 - Sergio Godoy
   👥 2 personas
   💵 Subtotal Reserva: $164,980
   🍾 Extras: $20,000
      (1x tabla_2_personas)
   💰 Total: $184,980

3. 14:00 - carolina seebach
   👥 2 personas
   💵 Subtotal Reserva: $139,980
   💰 Total: $139,980

... y 2 reservas más.
```

**Muestra máximo 8 reservas** (si hay más, indica cuántas faltan)

### 6. **Advertencias**

```
⚠️ Extras sin precio configurado: tabla_1, jugo_berries
```

Aparece cuando hay extras en las reservas que no tienen precio en la BD.

### 7. **Reservas Sin Completar** (si las hay)

```
========================================
⚠️ RESERVAS SIN COMPLETAR:

1. 17:00 - Juan Pérez
   📞 +56912345678
   🚤 HotBoat Trip 4 people

2. 20:00 - María González
   📞 +56987654321
   🚤 HotBoat Trip 2 people

========================================
👉 Por favor, completar la información de estas reservas en el formulario.
```

**Lógica de cruce (cómo detecta faltantes):**
1. Obtiene todas las reservas del día de `booknetic_appointments`
2. Obtiene todos los formularios del día de `Informacion Reservas`
3. Cruza por **fecha + hora** (con tolerancia de 15 minutos)
4. Si no encuentra match por hora, intenta cruzar por **nombre de cliente** (similitud >70%)
5. Las que no cruzan son "faltantes"

### 8. **Información Registrada**

```
========================================
🧾 INFORMACIÓN REGISTRADA:

1. javier figueroa
   🕘 07/03/2026 09:00
   🧾 Consumo: Sin consumo registrado
   ↔ Booknetic: javier figueroa • HotBoat Trip 5 people • 5 pax • CLP $194.950

2. Sergio Godoy
   🕘 07/03/2026 11:00
   🧾 Consumo: 1 x tabla_2_personas
   ↔ Booknetic: Sergio Godoy • HotBoat Trip 2 people • 2 pax • CLP $164.980
      Extras: 1 x tabla_2_personas

... y 3 reservas más con información completada.
```

**Muestra máximo 8 entradas** del formulario

---

## 🔧 Código que se Ejecuta

### 1. Chequeo de Hora (`check()`)

```python
# daily_summary_monitor.py líneas 88-110
async def check(self) -> List[Dict[str, Any]]:
    # Obtener hora actual en zona horaria Chile
    now_local = datetime.now(pytz.UTC).astimezone(self.timezone)
    current_time = now_local.time()
    current_date = now_local.date()
    
    # Verificar si es hora de enviar y no se ha enviado hoy
    if (current_time >= self.report_time and
            self.last_report_date != current_date):
        
        # Marcar como enviado hoy
        self.last_report_date = current_date
        
        # Retornar señal para generar reporte
        return [{"generate_report": True, "date": current_date}]
    
    return []
```

### 2. Generación del Reporte (`detect_changes()`)

```python
# daily_summary_monitor.py líneas 120-166
async def detect_changes(self, current_state):
    if not current_state or not current_state[0].get("generate_report"):
        return
    
    # Obtener datos de AYER
    yesterday = datetime.now().date() - timedelta(days=1)
    
    # 1. Contar reservas del día
    appointments_count = await self._count_appointments(yesterday)
    
    # 2. Contar información completada
    info_reservas_count = await self._count_info_reservas(yesterday)
    
    # 3. Obtener detalles de información completada
    info_details = await self._get_info_reservas_details(yesterday)
    
    # 4. Obtener resumen de consumos desde BD
    consumption_summary = await self._get_consumption_summary(...)
    
    # 5. Obtener reservas faltantes
    missing_details = await self._get_missing_reservas(yesterday, info_details)
    
    # 6. Calcular ingresos, costos y utilidades
    revenue_data = await self._calculate_revenue_for_date(yesterday)
    
    # 7. Generar y enviar el email
    await self._send_daily_report(
        yesterday,
        appointments_count,
        info_reservas_count,
        missing_details,
        info_details,
        consumption_summary,
        revenue_data
    )
```

### 3. Cálculo de Ingresos (`_calculate_revenue_for_date()`)

**Query principal** (líneas 1703-1765):

```sql
WITH appointments_data AS (
    SELECT 
        ba.id as appointment_id,
        DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
        TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
        -- Extraer el pago (precio final descontado)
        CAST(
            REGEXP_REPLACE(
                REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                '[^0-9]',
                '',
                'g'
            ) AS NUMERIC
        ) as payment_amount,
        ba.raw as appointment_raw,
        -- Row number para matching 1 a 1
        ROW_NUMBER() OVER (
            PARTITION BY DATE(...), TIME(...)
            ORDER BY ba.id
        ) as appointment_row_num
    FROM booknetic_appointments ba
    WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = %s
),
reservations_with_extras AS (
    SELECT 
        ir.id as reservation_id,
        TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
        ir.raw->>'horario_salida' as horario_salida,
        ir.raw as extras_json,  -- Aquí están los extras!
        ROW_NUMBER() OVER (...) as reservation_row_num
    FROM "Informacion Reservas" ir
    WHERE ir.raw->>'fecha' IS NOT NULL
)
SELECT 
    ad.*,
    r.extras_json
FROM appointments_data ad
LEFT JOIN reservations_with_extras r 
    ON ad.appointment_date = r.reservation_date
    AND TO_CHAR(ad.appointment_datetime, 'HH24:MI:SS') = r.horario_salida
    AND ad.appointment_row_num = r.reservation_row_num  -- ¡Clave para 1 a 1!
```

**Extracción de extras** (líneas 1640-1690):

```python
def _extract_extras_from_json(self, raw_json, prices, category_aliases, missing_prices):
    extras_list = []
    
    # Prefijos que indican un extra
    extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 
                      'otros_alcoholes', 'cha']
    
    for key, value in raw_json.items():
        # ¿Es un campo de extra?
        if any(key.lower().startswith(prefix) for prefix in extra_prefixes):
            
            # Extraer cantidad
            quantity = int(value) if value else 0
            
            # Extraer nombre del alias [nombre]
            alias_match = re.search(r'\[(.+?)\]', key)
            alias = alias_match.group(1) if alias_match else key
            
            # Buscar precio usando aliases
            price, category = self._find_price_for_extra(alias, prices, category_aliases)
            
            if price == 0:
                missing_prices.add(alias)  # Reportar faltante
            
            extras_list.append({
                'nombre': alias,
                'cantidad': quantity,
                'precio_unitario': price,
                'subtotal': price * quantity,
                'categoria': category
            })
    
    return extras_list
```

### 4. Sistema de Aliases para Extras

**Definido en `_get_category_aliases()`** (líneas 1434-1561):

```python
category_aliases = {
    # Champañas
    'champana_riccadona': [
        'champana_riccadonna_ruby',
        'champana_riccadonna_moscato_rose',
        'riccadonna_ruby',
        'riccadonna'
    ],
    
    # Cervezas
    'cerveza_artesanal': [
        'cerveza_artesanal_ambar',
        'cerveza_artesanal_negra',
        'artesanal_ambar'
    ],
    'cerveza_royal': [
        'cerveza_royal',
        'royal'
    ],
    
    # Bebidas
    'lata_bebida': [
        'coca_cola',
        'coca-cola',
        'fanta',
        'sprite'
    ],
    'jugo_1l': [
        'jugo_naranja',
        'jugo_berries',
        'naranja',
        'berries'
    ],
    
    # Tablas
    'tabla_4_personas': [
        'tabla_1_persona',
        'tabla_1',
        'tabla_4'
    ],
    
    # Extras especiales
    'romantic': [
        'modo_romantico',
        'pack_romantico',
        'pack_iluminacion_velas_y_letras'
    ],
    
    # Videos
    'video_15_seg': [
        'video_15_segundos',
        'video_15'
    ],
    'video_1_min': [
        'video_60_segundos',
        'video_60'
    ]
}
```

**¿Cómo funciona?**
1. El formulario tiene `extras[champana_riccadonna_ruby]` = `2`
2. El sistema busca en aliases y encuentra que `champana_riccadonna_ruby` mapea a `champana_riccadona`
3. Busca `champana_riccadona` en la tabla `Precios Extras`
4. Encuentra: Precio = $12,000, Costo = $6,000
5. Calcula: Ingreso = 2 × $12,000 = $24,000, Costo = 2 × $6,000 = $12,000

### 5. Cruce de Reservas (matching)

**Método principal: `_match_reservas_by_datetime()`** (líneas 338-433)

**Paso 1: Cruce por fecha + hora**

```python
# Para cada appointment
for appt in appointments:
    appt_dt = self._appointment_local_datetime(appt)  # ej: 2026-03-07 09:00
    
    # Buscar formulario con fecha/hora similar (±15 min)
    matched_slot = self._find_matching_slot(appt_dt, info_slots, used_slots)
    
    if matched_slot is not None:
        used_slots.add(matched_slot)  # Marcar como usado
        matched += 1
    else:
        missing.append(appt)  # Sin información
```

**Paso 2: Cruce por nombre (fallback)**

Si no encontró match por hora, intenta por nombre:

```python
def _match_by_customer_name(self, appointments, info_slots, used_slots):
    for appt in appointments:
        customer_name = appt.get('customer_name').lower()
        
        # Normalizar (quitar acentos, espacios)
        customer_normalized = self._normalize_name(customer_name)
        
        # Buscar en formularios no usados
        for idx, slot in enumerate(info_slots):
            if idx in used_slots:
                continue
            
            info_name = slot['entry'].get('nombre_cliente').lower()
            info_normalized = self._normalize_name(info_name)
            
            # Calcular similitud (intersección de palabras / unión)
            score = self._calculate_name_similarity(customer_normalized, info_normalized)
            
            if score > 0.7:  # Más de 70% similar
                used_slots.add(idx)
                matched_count += 1
                break
```

**Tolerancia de hora:**
- Configurable en `config.yaml`: `match_tolerance_minutes: 15`
- Por defecto: **15 minutos**
- Si appointment es 09:00 y formulario es 09:10, cruzan ✅
- Si appointment es 09:00 y formulario es 09:20, NO cruzan ❌

---

## 🎛️ Configuraciones Personalizables

### En `config.yaml`:

```yaml
daily_summary:
  enabled: true  # ¿Activar el monitor?
  check_interval: 300  # Cada cuánto chequear (segundos)
  report_time: "09:00"  # Hora de envío (24h)
  timezone: "America/Santiago"  # Zona horaria
  match_tolerance_minutes: 15  # Tolerancia para cruce
```

### Cambiar la hora de envío:

```yaml
report_time: "08:00"  # Enviar a las 8 AM
```

### Cambiar tolerancia de cruce:

```yaml
match_tolerance_minutes: 30  # Permitir hasta 30 min de diferencia
```

### Desactivar el monitor:

```yaml
enabled: false
```

---

## 🧪 Probar el Resumen Diario

### Opción 1: Esperar a las 09:00 AM

El sistema enviará automáticamente el reporte.

### Opción 2: Forzar envío inmediato

Edita temporalmente el código y reinicia:

```python
# daily_summary_monitor.py línea 105
# Cambiar:
self.last_report_date = current_date

# Por:
self.last_report_date = None  # Permitirá reenviar
```

### Opción 3: Crear script de prueba

```python
# scripts/test_daily_summary.py
import asyncio
from datetime import datetime, timedelta
from app.config import get_settings, load_yaml_config
from app.notifications.manager import NotificationManager
from app.monitors.daily_summary_monitor import DailySummaryMonitor

async def test():
    settings = get_settings()
    config = load_yaml_config()
    
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    monitor = DailySummaryMonitor(
        settings=settings,
        config=config.get("monitors", {}).get("daily_summary", {}),
        notification_manager=notification_manager
    )
    await monitor.initialize()
    
    # Forzar generación del reporte para ayer
    yesterday = datetime.now().date() - timedelta(days=1)
    await monitor.detect_changes([{"generate_report": True, "date": yesterday}])
    
    await notification_manager.close()

if __name__ == "__main__":
    asyncio.run(test())
```

Ejecutar:
```bash
python scripts/test_daily_summary.py
```

---

## ⚙️ Ajustes Comunes

### 1. Agregar nuevos aliases de extras

Editar `daily_summary_monitor.py` línea 1434:

```python
def _get_category_aliases(self):
    return {
        # ... aliases existentes ...
        
        # Agregar nuevo alias
        'cerveza_nueva': [
            'cerveza_nueva_marca',
            'nueva_marca',
            'marca_nueva'
        ],
    }
```

### 2. Cambiar costos fijos

Editar `daily_summary_monitor.py` línea 1383:

```python
COSTO_GAS_POR_RESERVA = 20000  # Cambiar de 15000 a 20000
COSTO_LEÑA_POR_RESERVA = 1500  # Cambiar de 1000 a 1500
# ...
COSTO_FIJO_TOTAL = 23500  # Actualizar total
```

### 3. Cambiar límites de visualización

```python
# Línea 601: Máximo de info a mostrar
limit = 8  # Cambiar a 10, 15, etc.

# Línea 1227: Máximo de faltantes a mostrar
for i, reserva in enumerate(missing_details[:10], 1):  # Cambiar [:10] a [:20]
```

### 4. Agregar filtros

Ejemplo: Excluir reservas canceladas o rechazadas

```python
# Línea 181 en _count_appointments
WHERE ...
  AND (status IS NULL OR status NOT IN ('canceled', 'rejected'))
```

---

## 📝 Notas Importantes

### 1. **Fuente de Ingresos de Reservas**

⚠️ **IMPORTANTE**: El sistema usa `booknetic_appointments.raw->>'payment'` como precio base de la reserva.

- ✅ Este es el precio **final** que pagó el cliente (ya con descuentos)
- ✅ Es más confiable que calcular desde precios base
- ❌ **NO** usa tabla de precios base × personas

**Ejemplo:**
- Precio lista 4 personas: $189,960
- Cliente tiene descuento: -$10,000
- `payment` en BD: $179,960 ← Este valor se usa ✅

### 2. **Fuente de Extras**

Los extras se leen **solo** desde `Informacion Reservas` (el formulario), **NO** desde `booknetic_appointments.extras`.

**Razón:** El formulario tiene información más detallada y confiable de consumos.

### 3. **Cruce 1 a 1 con ROW_NUMBER()**

Cuando hay múltiples reservas a la misma hora (ej: 2 reservas a las 09:00), el sistema usa `ROW_NUMBER()` para hacer matching 1 a 1:

```
Appointments         Información Reservas
09:00 #1 (row 1) → 09:00 #1 (row 1) ✅
09:00 #2 (row 2) → 09:00 #2 (row 2) ✅
```

Sin `ROW_NUMBER()`, podrían cruzarse incorrectamente.

### 4. **Costos de Extras desde BD**

Los costos variables (extras) se leen desde `Precios Extras.costo`, **NO** están hardcodeados.

Para actualizar un costo:
1. Editar la tabla `Precios Extras` en la BD
2. Modificar la columna `costo` del extra correspondiente
3. El próximo reporte usará el nuevo costo automáticamente

### 5. **Logs Detallados**

El monitor genera logs muy detallados para debugging:

```
🧾 Información Reservas (5) para 2026-03-07:
   - #1 javier figueroa | fecha_form='07/03/2026' | hora_form='09:00' | datetime_local=2026-03-07 09:00
   - #2 Sergio Godoy | fecha_form='07/03/2026' | hora_form='11:00' | datetime_local=2026-03-07 11:00
   ...

📅 Booknetic Appointments (5) para 2026-03-07:
   - javier figueroa | starts_at=2026-03-07 09:00 | local=2026-03-07 09:00 | servicio=HotBoat Trip 5 people
   - Sergio Godoy | starts_at=2026-03-07 11:00 | local=2026-03-07 11:00 | servicio=HotBoat Trip 2 people
   ...

🔗 Coincidencias por fecha/hora: 5/5
✅ Todas las reservas tienen información según fecha/hora.
```

Ver logs en Railway:
```bash
railway logs --tail | grep "Resumen Diario"
```

---

## 🆘 Solución de Problemas

### Problema: No recibí el email

**Verificar:**
1. ¿Está habilitado? `config.yaml` → `daily_summary.enabled: true`
2. ¿Email configurado? Variables de entorno `EMAIL_ENABLED=true`
3. Ver logs: `railway logs | grep "Reporte diario"`

**Logs esperados:**
```
⏰ Es hora de enviar el reporte diario (09:05 America/Santiago)
📊 Generando reporte diario...
✅ Reporte diario enviado por Email
```

### Problema: Los ingresos no coinciden

**Causas comunes:**
1. **Extras sin precio**: Revisa la sección "⚠️ Extras sin precio configurado"
2. **Cruce incorrecto**: Revisa los logs de matching
3. **Descuentos no reflejados**: El sistema usa `payment`, que ya incluye descuentos

**Debug:**
```python
# Agregar logs temporales en _calculate_revenue_for_date
logger.info(f"Payment amount: {payment_amount}, Extras: {extras_total}")
```

### Problema: Reservas marcadas como faltantes incorrectamente

**Causas:**
1. **Diferencia de hora > 15 min**: Aumentar `match_tolerance_minutes`
2. **Formato de fecha/hora incorrecto**: Revisar logs de parsing
3. **Nombre diferente**: El fallback por nombre requiere >70% similitud

**Solución:**
```yaml
# Aumentar tolerancia
match_tolerance_minutes: 30
```

### Problema: Extras mal categorizados

**Causa:** Nombre del extra no está en aliases

**Solución:**
Agregar alias en `_get_category_aliases()`:

```python
'categoria_existente': [
    'nombre_nuevo',
    'variante_nueva'
]
```

---

## 📚 Archivos Relacionados

- **Monitor**: `app/monitors/daily_summary_monitor.py` (1920 líneas)
- **Configuración**: `config.yaml` líneas 66-71
- **Notificador de email**: `app/notifications/email_notifier.py`
- **Variables de entorno**: `.env` → `EMAIL_*`, `RESEND_*`

---

**Última actualización**: 08/03/2026
