# Flujo de Consumo de Inventario 📦

## Resumen del Sistema

El sistema automatizado gestiona el inventario de forma automática cuando se crean nuevas reservas. El flujo es el siguiente:

```
┌──────────────────────────┐
│  Información Reservas    │  ← Nueva fila insertada (desde formulario/Google Sheets)
│  (tabla externa)         │
└────────────┬─────────────┘
             │
             │ TRIGGER: fn_info_reservas_to_consumption()
             │ (se ejecuta automáticamente al insertar)
             ↓
┌──────────────────────────┐
│  reservation_consumption │  ← Se crean filas con status='pending'
│  (tabla intermedia)      │     - Parsea el JSON de la reserva
└────────────┬─────────────┘     - Extrae productos y cantidades
             │                   - Mapea nombres → SKUs
             │
             │ MONITOR: ConsumptionMonitor
             │ (se ejecuta cada 30 segundos)
             ↓
┌──────────────────────────┐
│      inventory           │  ← Stock actualizado automáticamente
│  (tabla principal)       │     - Descuenta cantidad
└──────────────────────────┘     - Marca consumo como 'processed'
                                  - Envía alerta si stock bajo
```

## Componentes del Sistema

### 1. Tabla `inventory` ✅
**Ubicación**: Base de datos PostgreSQL  
**Creación**: `scripts/create_inventory_from_scratch.sql`

Contiene 31 productos con sus SKUs únicos:
- 7 Cervezas (CRV-*)
- 4 Champaña (CHP-*)
- 3 Licores (LIC-*)
- 3 Vinos (VIN-*)
- 5 Bebidas y Jugos (BEB-*, JUG-*)
- 2 Tablas (TBL-*)
- 7 Extras (EXT-*)

**Campos principales**:
- `id`: ID único
- `product_name`: Nombre del producto
- `sku`: Código único (CRV-ROYAL, BEB-COCA, etc.)
- `quantity`: Stock actual
- `min_stock`: Stock mínimo para alertas
- `category`: Categoría del producto

### 2. Tabla `reservation_consumption` ✅
**Ubicación**: Base de datos PostgreSQL  
**Creación**: `setup_database.sql` (líneas 150-161)

Tabla intermedia que registra los consumos pendientes de procesar.

**Campos principales**:
- `id`: ID único
- `reservation_id`: ID de la reserva en "Información Reservas"
- `item_sku`: SKU del producto (puede ser NULL si no se encuentra)
- `item_name`: Nombre del producto extraído del JSON
- `quantity`: Cantidad a descontar
- `status`: 'pending', 'processed', 'error', 'skipped'
- `processed_at`: Timestamp de cuando se procesó (NULL si está pendiente)
- `note`: Notas o mensajes de error

### 3. Trigger: `fn_info_reservas_to_consumption()` ✅
**Ubicación**: `setup_database.sql` (líneas 179-314)  
**Tipo**: AFTER INSERT trigger en tabla "Información Reservas"

**Función**:
1. Se dispara automáticamente cuando se inserta una fila en "Información Reservas"
2. Parsea el campo `raw` (JSONB) buscando claves como:
   - `extras_tipo_X_[alias]`
   - `cervezas_tipo_X_[alias]`
   - `tablas_[alias]`
   - `bebidas_y_jugos_tipo_X_[alias]`
   - `otros_alcoholes_tipo_X_[alias]`
   - `cha_tipo_X_[alias]`

3. Para cada producto encontrado:
   - Extrae el alias entre corchetes: `extras_tipo_1_[cerveza_royal]` → `cerveza_royal`
   - Convierte el alias a nombre legible: `cerveza_royal` → `Cerveza Royal`
   - Mapea el alias a un SKU usando el CASE statement (líneas 244-318)
   - Inserta una fila en `reservation_consumption` con status='pending'

**Mapeo de aliases a SKUs** (ejemplos):
```sql
-- Variaciones soportadas:
'cerveza_royal' → 'CRV-ROYAL'
'royal' → 'CRV-ROYAL'
'coca_cola' → 'BEB-COCA'
'coca-cola' → 'BEB-COCA'
'coca cola' → 'BEB-COCA'
'tabla_2_personas' → 'TBL-2P'
'tabla_2' → 'TBL-2P'
'tabla 2 personas' → 'TBL-2P'
```

### 4. Monitor: `ConsumptionMonitor` ✅
**Ubicación**: `app/monitors/consumption_monitor.py`  
**Configuración**: `config.json` (sección "consumption_monitor")

**Función**:
1. Se ejecuta automáticamente cada 30 segundos (configurable)
2. Consulta `reservation_consumption` buscando filas con `processed_at IS NULL`
3. Para cada consumo pendiente:
   - Busca el producto en `inventory` por SKU o por nombre
   - Descuenta la cantidad del stock actual
   - Marca el consumo como 'processed'
   - Si el stock queda bajo el mínimo, envía una notificación

**Búsqueda inteligente de productos**:
1. Primero busca por SKU (más preciso)
2. Si no encuentra, busca por nombre (case-insensitive)
3. Prioriza filas con SKU no nulo si hay duplicados

**Estados de consumo**:
- `pending`: Recién creado, esperando procesamiento
- `processed`: Stock actualizado exitosamente
- `error`: Error al procesar (producto no encontrado, etc.)
- `skipped`: Cantidad inválida o cero

## Flujo Completo de Ejemplo

### Escenario: Cliente hace una reserva con productos

1. **Se inserta una fila en "Información Reservas"**:
```json
{
  "nombre_cliente": "Juan Pérez",
  "fecha_reserva": "2025-11-15",
  "extras_tipo_1_[cerveza_royal]": "3",
  "bebidas_y_jugos_tipo_1_[coca_cola]": "2",
  "tablas_[tabla_2_personas]": "1",
  "extras_tipo_2_[toalla]": "5"
}
```

2. **El trigger se ejecuta automáticamente** y crea 4 filas en `reservation_consumption`:
```
| id | reservation_id | item_sku   | item_name         | quantity | status  |
|----|----------------|------------|-------------------|----------|---------|
| 1  | 123           | CRV-ROYAL  | Cerveza Royal     | 3        | pending |
| 2  | 123           | BEB-COCA   | Coca Cola         | 2        | pending |
| 3  | 123           | TBL-2P     | Tabla 2 Personas  | 1        | pending |
| 4  | 123           | EXT-TOALLA | Toalla            | 5        | pending |
```

3. **ConsumptionMonitor detecta los consumos pendientes** (máximo 30 segundos después):
   - Procesa cada consumo en orden
   - Para cada uno:
     ```sql
     UPDATE inventory SET quantity = quantity - X WHERE sku = 'SKU-XXX'
     ```
   - Marca el consumo como 'processed'

4. **Stock actualizado en `inventory`**:
```
ANTES:
| sku        | product_name      | quantity |
|------------|-------------------|----------|
| CRV-ROYAL  | Cerveza Royal     | 50       |
| BEB-COCA   | Coca-cola         | 100      |
| TBL-2P     | Tabla 2 Personas  | 10       |
| EXT-TOALLA | Toalla            | 30       |

DESPUÉS:
| sku        | product_name      | quantity |
|------------|-------------------|----------|
| CRV-ROYAL  | Cerveza Royal     | 47       | (-3)
| BEB-COCA   | Coca-cola         | 98       | (-2)
| TBL-2P     | Tabla 2 Personas  | 9        | (-1)
| EXT-TOALLA | Toalla            | 25       | (-5)
```

5. **Si algún producto quedó bajo el stock mínimo**:
   - Se envía una notificación automática vía WhatsApp/Telegram
   - Ejemplo: "🟡 Stock Bajo: Tabla 2 Personas tiene 9 unidades (mínimo: 10)"

## Scripts Disponibles

### `create_inventory_from_scratch.sql`
Crea la tabla `inventory` desde cero con todos los productos y SKUs predefinidos.

**Uso**:
```bash
psql -h HOST -U USER -d DATABASE -f scripts/create_inventory_from_scratch.sql
```

### `test_consumption_flow.sql`
Script de prueba que simula el flujo completo. Útil para verificar que todo funciona.

**Uso**:
```bash
psql -h HOST -U USER -d DATABASE -f scripts/test_consumption_flow.sql
```

### `setup_database.sql`
Script principal que crea todas las tablas, triggers y funciones del sistema.

## Verificación del Sistema

### 1. Verificar que el trigger existe:
```sql
SELECT 
    trigger_name, 
    event_manipulation, 
    event_object_table 
FROM information_schema.triggers 
WHERE trigger_name = 'trg_info_reservas_after_insert';
```

### 2. Verificar consumos pendientes:
```sql
SELECT * FROM reservation_consumption 
WHERE status = 'pending' 
ORDER BY created_at DESC;
```

### 3. Verificar stock actual:
```sql
SELECT 
    sku, 
    product_name, 
    quantity, 
    min_stock,
    CASE 
        WHEN quantity <= min_stock THEN '🔴 BAJO'
        WHEN quantity <= min_stock * 1.5 THEN '🟡 ALERTA'
        ELSE '🟢 OK'
    END as estado
FROM inventory 
ORDER BY category, sku;
```

### 4. Verificar consumos procesados recientemente:
```sql
SELECT 
    rc.id,
    rc.reservation_id,
    rc.item_sku,
    rc.item_name,
    rc.quantity,
    rc.status,
    rc.processed_at,
    i.quantity as stock_actual
FROM reservation_consumption rc
LEFT JOIN inventory i ON i.sku = rc.item_sku
WHERE rc.processed_at > NOW() - INTERVAL '1 hour'
ORDER BY rc.processed_at DESC;
```

## Configuración del Monitor

En `config.json`:
```json
{
  "consumption_monitor": {
    "enabled": true,
    "check_interval": 30,
    "table_name": "reservation_consumption",
    "notification_channel": "whatsapp",
    "batch_limit": 100
  }
}
```

**Parámetros**:
- `enabled`: Activar/desactivar el monitor
- `check_interval`: Intervalo en segundos entre chequeos (30 = chequea cada 30s)
- `table_name`: Nombre de la tabla de consumos
- `notification_channel`: Canal para notificaciones de stock bajo ("whatsapp", "telegram", o "all")
- `batch_limit`: Máximo de consumos a procesar por ciclo

## Solución de Problemas

### Problema: Los consumos no se crean en reservation_consumption
**Causa**: El trigger no existe o no se disparó
**Solución**:
1. Verificar que la tabla "Información Reservas" existe
2. Re-ejecutar `setup_database.sql` para crear el trigger
3. Verificar que el campo `raw` es tipo JSONB

### Problema: Los consumos quedan en 'pending' sin procesarse
**Causa**: El ConsumptionMonitor no está ejecutándose
**Solución**:
1. Verificar que el monitor está habilitado en `config.json`
2. Verificar logs: `tail -f logs/app.log`
3. Reiniciar el sistema: `python main.py`

### Problema: Consumos marcan 'error' con "Producto no encontrado"
**Causa**: El alias no está mapeado a un SKU o el producto no existe en inventory
**Solución**:
1. Verificar el alias en el trigger (líneas 244-318 de setup_database.sql)
2. Añadir el mapeo si falta
3. Verificar que el producto existe: `SELECT * FROM inventory WHERE sku = 'SKU-XXX'`
4. Re-ejecutar el trigger después de corregir

### Problema: Stock negativo
**Causa**: No debería ocurrir, el código previene esto (líneas 96-98)
**Solución**:
- El sistema automáticamente pone el stock en 0 si el cálculo da negativo
- Revisar manualmente y ajustar: `UPDATE inventory SET quantity = X WHERE sku = 'SKU-XXX'`

## Mantenimiento

### Añadir un nuevo producto:
```sql
INSERT INTO inventory (product_name, sku, category, quantity, min_stock)
VALUES ('Nuevo Producto', 'CAT-NUEVO', 'Categoria', 0, 5);

-- Luego añadir el mapeo en el trigger (setup_database.sql línea ~244):
WHEN 'nuevo_producto' THEN 'CAT-NUEVO'
WHEN 'alias_alternativo' THEN 'CAT-NUEVO'
```

### Limpiar consumos antiguos procesados:
```sql
-- Eliminar consumos procesados hace más de 30 días
DELETE FROM reservation_consumption 
WHERE status = 'processed' 
AND processed_at < NOW() - INTERVAL '30 days';
```

### Reintentar consumos con error:
```sql
-- Marcar consumos con error como pending para reintentar
UPDATE reservation_consumption 
SET status = 'pending', 
    processed_at = NULL, 
    note = NULL 
WHERE status = 'error' 
AND created_at > NOW() - INTERVAL '1 day';
```

## Conclusión

El sistema está completamente configurado y funcional:

✅ Tabla `inventory` con 31 productos y SKUs únicos  
✅ Trigger automático que parsea reservas y crea consumos  
✅ Monitor que procesa consumos cada 30 segundos  
✅ Actualización automática de stock  
✅ Notificaciones cuando el stock está bajo  
✅ Manejo de errores y estados  

**El flujo es completamente automático**: solo necesitas que el sistema esté ejecutándose (`python main.py`) y las reservas se procesarán automáticamente.

