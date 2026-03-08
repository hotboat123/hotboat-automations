# 🔄 Nueva Arquitectura: Tabla Materializada `reservas_con_extras`

## 🎯 Problema Anterior

Cada monitor (diario, semanal, mensual) duplicaba toda la lógica de cruce de datos:
- ❌ Código duplicado en múltiples archivos
- ❌ Consultas SQL complejas repetidas
- ❌ Difícil de mantener y debuggear
- ❌ Procesamiento pesado en cada ejecución

## ✅ Nueva Solución

Crear una **tabla materializada** llamada `reservas_con_extras` que almacena los datos ya cruzados:

```
booknetic_appointments + Informacion Reservas + Precios Extras
                    ↓
         reservas_con_extras (tabla BD)
                    ↓
    Resúmenes (diario, semanal, mensual)
```

---

## 📊 Estructura de la Tabla

### Tabla: `reservas_con_extras`

```sql
CREATE TABLE reservas_con_extras (
    id SERIAL PRIMARY KEY,
    
    -- IDs
    appointment_id TEXT NOT NULL,
    reservation_id TEXT,
    
    -- Fecha y hora
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    
    -- Cliente
    nombre_cliente TEXT,
    email TEXT,
    telefono TEXT,
    
    -- Servicio
    servicio TEXT,
    num_personas INTEGER,
    
    -- Ingresos
    ingreso_reserva NUMERIC(10, 2),
    ingreso_extras NUMERIC(10, 2),
    ingreso_total NUMERIC(10, 2),
    
    -- Costos
    costo_operativo_fijo NUMERIC(10, 2),      -- $18,000 fijo
    costo_operativo_variable NUMERIC(10, 2),
    costo_operativo_total NUMERIC(10, 2),
    
    -- Datos adicionales
    num_adultos INTEGER,
    num_ninos INTEGER,
    ciudad_origen TEXT,
    como_supieron TEXT,
    clima_del_dia TEXT,
    categoria_clientes TEXT,
    tipo_clientes TEXT,
    
    -- Estado
    status TEXT,
    tiene_cruce BOOLEAN,
    
    -- Extras (JSON)
    extras_json JSONB,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (appointment_id, fecha)
);
```

---

## 🚀 Componentes del Sistema

### 1. **Migración SQL**
**Archivo**: `database/migrations/005_create_reservas_con_extras.sql`

Crea la tabla con:
- Estructura completa
- Índices para búsquedas rápidas
- Trigger para `updated_at` automático
- Comentarios de documentación

### 2. **Script de Sincronización**
**Archivo**: `scripts/sync_reservas_con_extras.py`

Sincroniza los datos desde las tablas originales a `reservas_con_extras`.

**Uso:**
```bash
# Sincronizar últimos 30 días (por defecto)
python scripts/sync_reservas_con_extras.py

# Sincronizar periodo específico
python scripts/sync_reservas_con_extras.py 2026-01-01 2026-03-02

# Forzar recreación (borrar y volver a crear)
python scripts/sync_reservas_con_extras.py 2026-01-01 2026-03-02 --force
```

**Atajos:**
```bash
# Linux/Mac
./sync_reservas.sh 2026-01-01 2026-03-02

# Windows
sync_reservas.bat 2026-01-01 2026-03-02
```

### 3. **Monitor Automático**
**Archivo**: `app/monitors/reservas_sync_monitor.py`

Se ejecuta automáticamente cada **10 minutos** y sincroniza los últimos **7 días**.

**Configuración** (`config.yaml`):
```yaml
monitors:
  reservas_sync:
    enabled: true
    check_interval: 600  # 10 minutos
    lookback_days: 7     # últimos 7 días
```

**Funcionamiento:**
1. Chequea cada 10 minutos si hay datos nuevos
2. Sincroniza últimos 7 días automáticamente
3. Actualiza registros existentes (usa `ON CONFLICT`)
4. Notifica si hay errores

### 4. **Resumen Diario Simplificado** (próximo)
En lugar de la lógica compleja actual, el resumen diario hará queries simples:

```sql
-- Ingresos del día
SELECT 
    SUM(ingreso_reserva) as total_reservas,
    SUM(ingreso_extras) as total_extras,
    SUM(ingreso_total) as total_ingresos,
    COUNT(*) as num_reservas
FROM reservas_con_extras
WHERE fecha = '2026-03-07';

-- Reservas sin cruce
SELECT * FROM reservas_con_extras
WHERE fecha = '2026-03-07' AND tiene_cruce = FALSE;

-- Detalle por reserva
SELECT * FROM reservas_con_extras
WHERE fecha = '2026-03-07'
ORDER BY hora;
```

---

## 📋 Flujo Completo

### Inicialización (primera vez):

```bash
# 1. Ejecutar migración
python scripts/run_migrations.py

# 2. Sincronizar datos históricos
python scripts/sync_reservas_con_extras.py 2025-01-01 2026-03-02 --force

# 3. Iniciar el sistema (monitor automático)
python main.py
```

### Operación Normal:

```
1. Nuevas reservas en booknetic_appointments
              ↓
2. Monitor (cada 10 min) detecta cambios
              ↓
3. Script sync_reservas_con_extras.py se ejecuta
              ↓
4. Tabla reservas_con_extras se actualiza
              ↓
5. Resumen diario (09:00 AM) lee de la tabla
              ↓
6. Email enviado con datos ya procesados
```

---

## 🔍 Consultas de Ejemplo

### Ingresos del mes actual:
```sql
SELECT 
    DATE_TRUNC('month', fecha) as mes,
    SUM(ingreso_total) as ingresos,
    SUM(costo_operativo_total) as costos,
    SUM(ingreso_total - costo_operativo_total) as utilidad
FROM reservas_con_extras
WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY DATE_TRUNC('month', fecha);
```

### Top 5 extras más vendidos:
```sql
SELECT 
    jsonb_object_keys(extras_json) as extra,
    COUNT(*) as veces_pedido,
    SUM((extras_json->>jsonb_object_keys(extras_json))::int) as cantidad_total
FROM reservas_con_extras
WHERE extras_json != '{}'
GROUP BY jsonb_object_keys(extras_json)
ORDER BY cantidad_total DESC
LIMIT 5;
```

### Reservas sin información completada:
```sql
SELECT 
    fecha, hora, nombre_cliente, servicio
FROM reservas_con_extras
WHERE tiene_cruce = FALSE
ORDER BY fecha DESC, hora DESC;
```

### Ingresos por ciudad:
```sql
SELECT 
    COALESCE(ciudad_origen, 'Sin ciudad') as ciudad,
    COUNT(*) as num_reservas,
    SUM(ingreso_total) as ingresos_totales
FROM reservas_con_extras
WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ciudad_origen
ORDER BY ingresos_totales DESC;
```

---

## ✨ Beneficios

### 1. **Simplicidad**
- ✅ Queries simples en lugar de JOINs complejos
- ✅ Código más legible y mantenible
- ✅ Menos bugs potenciales

### 2. **Performance**
- ✅ Consultas más rápidas (datos pre-procesados)
- ✅ Índices optimizados para búsquedas
- ✅ Menos carga en la BD en cada reporte

### 3. **Consistencia**
- ✅ Una única fuente de verdad
- ✅ Lógica de cruce en un solo lugar
- ✅ Actualizaciones atómicas

### 4. **Flexibilidad**
- ✅ Fácil agregar columnas nuevas
- ✅ Queries ad-hoc rápidas
- ✅ Exportaciones simples a CSV

### 5. **Debugging**
- ✅ Inspeccionar datos cruzados directamente en la BD
- ✅ Logs claros del proceso de sincronización
- ✅ Rollback fácil con `--force`

---

## 🔧 Mantenimiento

### Resincronizar datos:
```bash
# Todo el periodo
python scripts/sync_reservas_con_extras.py 2025-01-01 2026-03-02 --force

# Solo un día
python scripts/sync_reservas_con_extras.py 2026-03-07 2026-03-07 --force
```

### Ver logs del monitor:
```bash
railway logs --tail | grep "Sincronización de Reservas"
```

### Verificar tabla:
```sql
-- Contar registros
SELECT COUNT(*) FROM reservas_con_extras;

-- Últimas actualizaciones
SELECT fecha, COUNT(*) 
FROM reservas_con_extras 
GROUP BY fecha 
ORDER BY fecha DESC 
LIMIT 10;

-- Registros sin cruce
SELECT COUNT(*) 
FROM reservas_con_extras 
WHERE tiene_cruce = FALSE;
```

### Borrar datos de prueba:
```sql
DELETE FROM reservas_con_extras WHERE fecha = '2026-03-07';
```

---

## 🚧 Próximos Pasos

### 1. Migrar Resumen Diario
Modificar `daily_summary_monitor.py` para leer de `reservas_con_extras`:
- Eliminar lógica de cruce compleja
- Simplificar queries
- Mantener mismo formato de email

### 2. Migrar Resumen Semanal/Mensual
Similar al diario, simplificar queries.

### 3. Agregar Costos de Marketing
Incluir en la tabla:
```sql
ALTER TABLE reservas_con_extras 
ADD COLUMN costo_marketing NUMERIC(10, 2) DEFAULT 0;
```

### 4. Dashboard en Tiempo Real
Con la tabla materializada, es fácil crear dashboards con herramientas como:
- Grafana
- Metabase
- Superset

---

## 📚 Archivos Creados

1. ✅ `database/migrations/005_create_reservas_con_extras.sql` - Migración SQL
2. ✅ `scripts/sync_reservas_con_extras.py` - Script de sincronización
3. ✅ `app/monitors/reservas_sync_monitor.py` - Monitor automático
4. ✅ `sync_reservas.sh` / `sync_reservas.bat` - Atajos de shell
5. ✅ `config.yaml` - Configuración del monitor
6. ✅ `main.py` - Integración del monitor

---

**Última actualización**: 08/03/2026
