# Explicación del Cruce de Tablas

## Resumen

Para los análisis de resultados, cruzamos **3 tablas principales**:
1. `booknetic_appointments` - Datos de las citas/reservas
2. `booknetic_payments` - Datos de los pagos
3. `Informacion Reservas` - Datos de extras y detalles adicionales

## 1. Estructura de las Tablas

### Tabla: `booknetic_appointments`
Contiene información básica de cada cita:
```sql
- id: UUID único de la cita
- status: Estado (null, 'canceled', 'rejected')
- created_at: Fecha de creación
- raw->>'start_date': Fecha y hora de inicio (formato: 'DD/MM/YYYY HH24:MI')
- raw->>'customer': Nombre del cliente
- raw->>'email': Email del cliente
- raw->>'phone': Teléfono del cliente
- raw->>'service': Nombre del servicio
- raw->>'location': Ubicación
```

### Tabla: `booknetic_payments`
Contiene información de los pagos:
```sql
- id: UUID único del pago
- raw->>'appointment_date': Fecha de la cita (formato: 'DD/MM/YYYY HH24:MI')
- raw->>'payment': Monto pagado
- raw->>'status': Estado del pago
- raw->>'method': Método de pago
```

### Tabla: `Informacion Reservas`
Contiene detalles adicionales y extras:
```sql
- id: UUID único
- created_at: Fecha de creación
- raw->>'fecha': Fecha de la reserva (formato: 'DD/MM/YYYY')
- raw->>'horario_salida': Hora de salida (formato: 'HH:MI:SS')
- raw->>'nombre': Nombre del cliente
- raw->>'apellido': Apellido del cliente
- raw->>'telefono': Teléfono
- raw->>'email': Email
- raw->>'cantidad_personas': Número de personas
- raw->>'descuento': Descuento aplicado
- raw->>'notas': Notas adicionales
- raw->>'extras_*': Campos de extras (cervezas, tablas, etc.)
```

## 2. Lógica del Cruce (JOIN)

El cruce se hace utilizando **3 criterios**:

### Criterio 1: Fecha
Ambas tablas deben tener la misma **fecha** de reserva:
```sql
DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = 
TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY')
```

### Criterio 2: Hora de salida
Deben coincidir en la **hora exacta** (HH:MI:SS):
```sql
TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') = 
ir.raw->>'horario_salida'
```

### Criterio 3: Número de fila (ROW_NUMBER)
Para manejar múltiples reservas en la misma fecha/hora, usamos `ROW_NUMBER()`:
```sql
ROW_NUMBER() OVER (
    PARTITION BY fecha, hora
    ORDER BY id
) = ROW_NUMBER() OVER (
    PARTITION BY fecha, hora
    ORDER BY created_at
)
```

Esto asegura que:
- Si hay 2 reservas a las 10:00 AM, la primera de `appointments` se empareja con la primera de `Informacion Reservas`
- La segunda con la segunda, y así sucesivamente

## 3. Query SQL Completa

```sql
WITH appointments_data AS (
    -- Extraer y preparar datos de appointments
    SELECT 
        ba.id as appointment_id,
        DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
        TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as appointment_time,
        ba.raw->>'customer' as customer_name,
        -- ... más campos
        ROW_NUMBER() OVER (
            PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                         TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
            ORDER BY ba.id
        ) as ba_row_num
    FROM booknetic_appointments ba
    WHERE (ba.status IS NULL OR ba.status NOT IN ('canceled', 'rejected'))
),
payments_data AS (
    -- Extraer y preparar datos de payments
    SELECT 
        bp.id as payment_id,
        DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')) as payment_date,
        TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS') as payment_time,
        CAST(REGEXP_REPLACE(...) AS NUMERIC) as payment_amount,
        -- ... más campos
        ROW_NUMBER() OVER (
            PARTITION BY DATE(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI')),
                         TO_CHAR(TO_TIMESTAMP(bp.raw->>'appointment_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
            ORDER BY bp.id
        ) as bp_row_num
    FROM booknetic_payments bp
),
reservations_with_extras AS (
    -- Extraer y preparar datos de Informacion Reservas
    SELECT 
        ir.id as reservation_id,
        TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
        ir.raw->>'horario_salida' as horario_salida,
        ir.raw->>'nombre' as nombre_reserva,
        -- ... más campos
        ir.raw as extras_json,
        ROW_NUMBER() OVER (
            PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                         ir.raw->>'horario_salida'
            ORDER BY ir.created_at ASC
        ) as ir_row_num
    FROM "Informacion Reservas" ir
)
-- AQUÍ ESTÁ EL CRUCE:
SELECT 
    ad.*,
    pd.*,
    r.*
FROM appointments_data ad
LEFT JOIN payments_data pd
    ON ad.appointment_date = pd.payment_date        -- ✓ Misma fecha
    AND ad.appointment_time = pd.payment_time       -- ✓ Misma hora
    AND ad.ba_row_num = pd.bp_row_num              -- ✓ Mismo orden
LEFT JOIN reservations_with_extras r 
    ON ad.appointment_date = r.reservation_date     -- ✓ Misma fecha
    AND ad.appointment_time = r.horario_salida      -- ✓ Misma hora
    AND ad.ba_row_num = r.ir_row_num               -- ✓ Mismo orden
ORDER BY ad.appointment_date, ad.appointment_time
```

## 4. Procesamiento de Extras

Una vez hecho el cruce, procesamos los extras de `Informacion Reservas`:

### Paso 1: Identificar campos de extras
```python
extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']

for key, value in extras_json.items():
    if any(key.lower().startswith(prefix) for prefix in extra_prefixes):
        # Es un extra
```

### Paso 2: Extraer cantidad
```python
cantidad = int(str(value).strip()) if value else 0
```

### Paso 3: Extraer nombre del extra
El nombre está en corchetes: `extras[Cerveza Corona]`
```python
import re
alias_match = re.search(r'\[(.+?)\]', key)
if alias_match:
    extra_name = alias_match.group(1)  # "Cerveza Corona"
```

### Paso 4: Buscar precio y costo
```python
# Normalizar nombre para búsqueda
normalized_name = normalize_text(extra_name)

# Buscar en tabla "Precios Extras"
precio_unitario = find_cost_for_extra(normalized_name, prices_dict)
costo_unitario = find_cost_for_extra(normalized_name, costs_dict)

# Calcular totales
ingreso_extra = cantidad * precio_unitario
costo_extra = cantidad * costo_unitario
```

## 5. Cálculos Finales

### Ingresos
```python
ingreso_reserva = payment_amount  # Del payment
ingreso_extras = suma de (cantidad × precio) para cada extra
ingreso_total = ingreso_reserva + ingreso_extras
```

### Costos
```python
# Costos fijos por reserva
costo_gas = 15000
costo_leña = 1000
costo_agua = 1000
costo_hielo = 1000
costo_fijo = 18000

# Costos variables (extras)
costo_extras = suma de (cantidad × costo) para cada extra

# Costo operativo total
costo_operativo = costo_fijo + costo_extras

# Costo de marketing (de tabla marketing_costs)
costo_marketing = marketing_costs_by_date.get(fecha, 0)

# Costo total
costo_total = costo_operativo + costo_marketing
```

### Utilidades
```python
utilidad_bruta = ingreso_total - costo_operativo
utilidad_neta = ingreso_total - costo_total

margen_bruto = (utilidad_bruta / ingreso_total) × 100
margen_neto = (utilidad_neta / ingreso_total) × 100
```

## 6. Ejemplo Práctico

### Datos de entrada:

**booknetic_appointments:**
```
id: abc123
start_date: "01/01/2026 10:00"
customer: "Juan Pérez"
```

**booknetic_payments:**
```
id: def456
appointment_date: "01/01/2026 10:00"
payment: "$150.000"
```

**Informacion Reservas:**
```
id: ghi789
fecha: "01/01/2026"
horario_salida: "10:00:00"
extras[Cerveza Corona]: "6"
extras[Tabla 2 personas]: "1"
```

### Cruce:
✓ Fecha: 2026-01-01 = 2026-01-01 ✓
✓ Hora: 10:00:00 = 10:00:00 ✓
✓ Row number: 1 = 1 ✓

### Resultado del cruce:
```python
{
    'appointment_id': 'abc123',
    'payment_id': 'def456',
    'reservation_id': 'ghi789',
    'customer_name': 'Juan Pérez',
    'payment_amount': 150000,
    'extras': {
        'extras[Cerveza Corona]': '6',
        'extras[Tabla 2 personas]': '1'
    }
}
```

### Cálculos:
```python
# Extras
Cerveza Corona: 6 × 5000 = 30000
Tabla 2: 1 × 35000 = 35000
ingreso_extras = 65000

# Costos extras
Cerveza Corona: 6 × 2000 = 12000
Tabla 2: 1 × 20000 = 20000
costo_extras = 32000

# Totales
ingreso_total = 150000 + 65000 = 215000
costo_operativo = 18000 + 32000 = 50000
utilidad_bruta = 215000 - 50000 = 165000
margen_bruto = 76.7%
```

## 7. Script de Exportación

Creé el script `export_reservations_full.py` que:

1. ✅ Hace el cruce de las 3 tablas
2. ✅ Procesa todos los extras
3. ✅ Calcula costos y utilidades
4. ✅ Exporta un CSV consolidado con TODA la información

### Uso:
```bash
# Un día específico
python scripts/export_reservations_full.py 2026-01-01

# Rango de fechas
python scripts/export_reservations_full.py 2026-01-01 2026-01-31
```

### Columnas del CSV generado:
- Fecha, Hora
- IDs (Appointment, Payment, Reserva)
- Información del cliente (Nombre, Email, Teléfono)
- Detalles de la reserva (Servicio, Ubicación, Personas, Descuento, Notas)
- Ingresos (Reserva, Extras, Total)
- Costos (Op Fijo, Op Variable, Marketing, Total)
- Utilidades (Bruta, Neta, Márgenes)
- Extras vendidos
- Status y timestamps

## 8. Archivos Relacionados

- **Script principal:** `scripts/export_reservations_full.py`
- **Análisis diario:** `scripts/export_daily_analysis.py`
- **Cálculo mensual:** `scripts/calculate_month_revenue_optimized.py`
- **Monitor diario:** `app/monitors/daily_summary_monitor.py`
