# 🚀 Guía Rápida: Activar Tabla Materializada

## ✅ Paso 1: Crear la Tabla en Railway

### Opción A: Desde Railway CLI
```bash
railway connect postgres
```

Luego copia y pega esta query completa:

```sql
CREATE TABLE IF NOT EXISTS reservas_con_extras (
    id SERIAL PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    reservation_id TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    nombre_cliente TEXT,
    email TEXT,
    telefono TEXT,
    servicio TEXT,
    num_personas INTEGER,
    ingreso_reserva NUMERIC(10, 2) DEFAULT 0,
    ingreso_extras NUMERIC(10, 2) DEFAULT 0,
    ingreso_total NUMERIC(10, 2) DEFAULT 0,
    costo_operativo_fijo NUMERIC(10, 2) DEFAULT 18000,
    costo_operativo_variable NUMERIC(10, 2) DEFAULT 0,
    costo_operativo_total NUMERIC(10, 2) DEFAULT 18000,
    num_adultos INTEGER DEFAULT 0,
    num_ninos INTEGER DEFAULT 0,
    ciudad_origen TEXT,
    como_supieron TEXT,
    clima_del_dia TEXT,
    categoria_clientes TEXT,
    tipo_clientes TEXT,
    status TEXT,
    tiene_cruce BOOLEAN DEFAULT FALSE,
    extras_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_appointment_date UNIQUE (appointment_id, fecha)
);

CREATE INDEX IF NOT EXISTS idx_reservas_extras_fecha ON reservas_con_extras(fecha);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_appointment_id ON reservas_con_extras(appointment_id);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_reservation_id ON reservas_con_extras(reservation_id);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_fecha_hora ON reservas_con_extras(fecha, hora);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_tiene_cruce ON reservas_con_extras(tiene_cruce);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_created_at ON reservas_con_extras(created_at);

CREATE OR REPLACE FUNCTION update_reservas_extras_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_reservas_extras_updated_at ON reservas_con_extras;
CREATE TRIGGER trigger_update_reservas_extras_updated_at
    BEFORE UPDATE ON reservas_con_extras
    FOR EACH ROW
    EXECUTE FUNCTION update_reservas_extras_updated_at();
```

### Opción B: Desde Railway Dashboard
1. Ir a tu proyecto en railway.app
2. Click en tu base de datos PostgreSQL
3. Click en **"Data"** → **"Query"**
4. Pegar la query completa de arriba
5. Click en **"Run"**

---

## ✅ Paso 2: Verificar la Tabla

Ejecutar en Railway:

```sql
-- Ver que existe
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'reservas_con_extras';

-- Ver estructura
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'reservas_con_extras'
ORDER BY ordinal_position;

-- Debería estar vacía por ahora
SELECT COUNT(*) FROM reservas_con_extras;
-- Resultado esperado: 0
```

---

## ✅ Paso 3: El Código ya se Desplegó Automáticamente

El `git push` ya desplegó:
- ✅ Monitor automático (`reservas_sync_monitor.py`)
- ✅ Script de sincronización (`sync_reservas_con_extras.py`)
- ✅ Configuración en `config.yaml`

Railway detectará los cambios y:
1. Hará build del nuevo código
2. Reiniciará la aplicación
3. El monitor se activará automáticamente

---

## ✅ Paso 4: Sincronizar Datos Iniciales

Una vez que Railway termine de desplegar (2-3 minutos):

```bash
# Conectar a Railway
railway link

# Sincronizar últimos 30 días
railway run python scripts/sync_reservas_con_extras.py

# O periodo específico
railway run python scripts/sync_reservas_con_extras.py 2025-01-01 2026-03-02
```

**Alternativa:** Esperar 10 minutos y el monitor automático sincronizará los últimos 7 días.

---

## ✅ Paso 5: Verificar que Funcionó

```sql
-- Ver cuántos registros se crearon
SELECT COUNT(*) FROM reservas_con_extras;

-- Ver las fechas más recientes
SELECT fecha, COUNT(*) as num_reservas
FROM reservas_con_extras
GROUP BY fecha
ORDER BY fecha DESC
LIMIT 10;

-- Ver un registro completo
SELECT * FROM reservas_con_extras
ORDER BY created_at DESC
LIMIT 1;
```

---

## 🔍 Monitorear en Tiempo Real

```bash
# Ver logs de Railway
railway logs --tail

# Buscar logs del monitor
railway logs | grep "Sincronización de Reservas"

# Deberías ver líneas como:
# 🔄 Monitor de Sincronización de Reservas activado
# 🔄 Ejecutando sincronización inicial...
# 📅 Sincronizando periodo: 2026-02-28 a 2026-03-07
# ✅ Sincronización completada exitosamente
```

---

## 📊 Queries Útiles

### Ingresos del mes actual:
```sql
SELECT 
    SUM(ingreso_total) as ingresos,
    SUM(costo_operativo_total) as costos,
    SUM(ingreso_total - costo_operativo_total) as utilidad,
    COUNT(*) as num_reservas
FROM reservas_con_extras
WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE);
```

### Reservas sin información completada:
```sql
SELECT fecha, hora, nombre_cliente, servicio
FROM reservas_con_extras
WHERE tiene_cruce = FALSE
ORDER BY fecha DESC, hora DESC;
```

### Top 5 extras más vendidos (últimos 30 días):
```sql
SELECT 
    jsonb_object_keys(extras_json) as extra,
    COUNT(*) as veces_pedido,
    SUM((extras_json->>jsonb_object_keys(extras_json))::int) as cantidad_total
FROM reservas_con_extras
WHERE extras_json != '{}'
  AND fecha >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY jsonb_object_keys(extras_json)
ORDER BY cantidad_total DESC
LIMIT 5;
```

---

## ⚠️ Troubleshooting

### No se creó la tabla
```sql
-- Ver si hay error en la creación
SELECT * FROM pg_tables WHERE tablename = 'reservas_con_extras';

-- Si no existe, volver a ejecutar la query del Paso 1
```

### El monitor no se activó
```bash
# Ver logs
railway logs --tail

# Buscar errores
railway logs | grep ERROR

# Reiniciar manualmente
railway restart
```

### No hay datos en la tabla
```bash
# Sincronizar manualmente
railway run python scripts/sync_reservas_con_extras.py 2026-03-01 2026-03-07

# Ver si hubo errores en el output
```

---

## 🎉 ¡Listo!

Una vez completados estos pasos, tendrás:
- ✅ Tabla `reservas_con_extras` creada y funcionando
- ✅ Monitor sincronizando automáticamente cada 10 minutos
- ✅ Datos históricos cargados
- ✅ Sistema listo para usar en resúmenes diarios

**Próximo paso:** Modificar el resumen diario para leer de esta tabla (opcional, puedes hacerlo después).

---

**Duración total:** ~10 minutos
- Crear tabla: 1 minuto
- Deploy en Railway: 3 minutos
- Sincronización inicial: 5 minutos (dependiendo del volumen de datos)
