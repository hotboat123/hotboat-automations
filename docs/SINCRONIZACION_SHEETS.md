# Sincronización de Reservas con Extras a Google Sheets

## 📊 Resumen

Este sistema sincroniza automáticamente los datos de la tabla `reservas_con_extras` a Google Sheets para que puedas:
- Hacer análisis en Looker Studio
- Crear dashboards personalizados
- Trabajar con los datos en tiempo real

## 🏗️ Arquitectura

```
reservas_con_extras (PostgreSQL)
         ↓
ReservasSheetsSyncMonitor (cada 10 min)
         ↓
Reservas_Con_Extras_Sheets (tabla intermedia)
         ↓
hotboat-etl (sincronización a Google Sheets)
         ↓
Google Sheets → Looker Studio Dashboard
```

## 📋 Tabla de Datos Sincronizados

La sincronización incluye todos los campos de `reservas_con_extras`:

### Identificadores
- `id` - ID interno
- `appointment_id` - ID del appointment
- `reservation_id` - ID de la reserva

### Información Básica
- `fecha` - Fecha de la reserva
- `hora` - Hora de la reserva
- `nombre_cliente` - Nombre del cliente
- `email` - Email del cliente
- `telefono` - Teléfono del cliente
- `servicio` - Tipo de servicio contratado
- `num_personas` - Número de personas
- `status` - Estado de la reserva

### Ingresos
- `ingreso_reserva` - Ingreso base
- `ingreso_extras` - Ingreso por extras
- `ingreso_total` - Ingreso total

### Costos Operativos
- `costo_operativo_fijo` - Costo fijo ($18,000)
- `costo_operativo_variable` - Costo variable (extras)
- `costo_operativo_total` - Costo total

### Datos del Cliente
- `num_adultos` - Número de adultos
- `num_ninos` - Número de niños
- `ciudad_origen` - Ciudad de origen
- `como_supieron` - Cómo se enteraron de HotBoat
- `clima_del_dia` - Clima del día
- `categoria_clientes` - Categoría de clientes
- `tipo_clientes` - Tipo de clientes

### Metadatos
- `tiene_cruce` - Si cruzó con Información Reservas
- `extras_json` - Extras en formato JSON

## ⚙️ Configuración

### 1. Crear Tabla en Railway

Ejecuta este SQL en la base de datos de Railway:

```sql
-- Ver archivo: CREAR_TABLA_SHEETS.sql
```

O usa el comando:
```bash
railway run psql $DATABASE_URL < CREAR_TABLA_SHEETS.sql
```

### 2. Verificar Configuración

En `config.yaml`:

```yaml
monitors:
  reservas_sheets_sync:
    enabled: true
    name: "Monitor de Sincronización Reservas → Google Sheets"
    check_interval: 600  # cada 10 minutos
    sync_from_today: true  # Solo sincronizar desde HOY en adelante (no modifica fechas pasadas)
```

**IMPORTANTE:** Por defecto, el sistema solo sincroniza **desde la fecha actual en adelante** para preservar tus ediciones manuales en Google Sheets. Si necesitas sincronizar fechas pasadas, cambia `sync_from_today: false`.

### 3. Configurar Google Sheets (hotboat-etl)

En el proyecto `hotboat-etl`, configura la sincronización de la tabla `Reservas_Con_Extras_Sheets`:

1. Agregar credenciales de Google Sheets API
2. Configurar el ID de la hoja de destino
3. Mapear los campos de la tabla a las columnas

## 🔄 Funcionamiento

### Estructura de Datos

La tabla `Reservas_Con_Extras_Sheets` ahora tiene **columnas individuales** (formato tabular) en vez de un JSON gigante:

- **IDs**: `appointment_id`, `reservation_id`
- **Fecha/Hora**: `fecha`, `hora`
- **Cliente**: `nombre_cliente`, `email`, `telefono`
- **Servicio**: `servicio`, `num_personas`, `num_adultos`, `num_ninos`
- **Ingresos**: `ingreso_reserva`, `ingreso_extras`, `ingreso_total`
- **Costos**: `costo_operativo_fijo`, `costo_operativo_variable`, `costo_operativo_total`
- **Metadata**: `ciudad_origen`, `como_supieron`, `clima_del_dia`, `categoria_clientes`, `tipo_clientes`
- **Estado**: `status`, `tiene_cruce`
- **Extras**: `extras_json` (único campo JSON, opcional)

Esto hace que sea **mucho más fácil** consultar y analizar los datos directamente en la base de datos o en Google Sheets.

### Sincronización Automática

El monitor `ReservasSheetsSyncMonitor`:
1. Se ejecuta cada 10 minutos
2. Lee los datos de `reservas_con_extras` 
3. Los inserta/actualiza en `Reservas_Con_Extras_Sheets` con columnas individuales
4. `hotboat-etl` detecta los cambios y los sube a Google Sheets

### Sincronización Inteligente

- **Solo sincroniza fechas >= HOY** por defecto (preserva ediciones manuales en fechas pasadas)
- Para cambiar este comportamiento: `sync_from_today: false` en `config.yaml`

## 📊 Uso en Looker Studio

Una vez que los datos estén en Google Sheets:

1. **Conectar Google Sheets a Looker Studio**
   - En Looker Studio: "Crear" → "Fuente de datos"
   - Seleccionar "Google Sheets"
   - Elegir tu hoja sincronizada

2. **Crear Dashboards**
   - Ingresos por día/semana/mes
   - Análisis de extras
   - Comparación de costos vs ingresos
   - Rentabilidad por tipo de cliente
   - Origen de clientes
   - Clima vs reservas

3. **Métricas Calculadas**
   ```
   Utilidad = ingreso_total - costo_operativo_total
   Margen = (Utilidad / ingreso_total) * 100
   Ticket Promedio = ingreso_total / num_personas
   ```

## 🚀 Primeros Pasos

### Paso 1: Crear la Tabla

```bash
# Ejecutar migración en Railway
railway run psql $DATABASE_URL < CREAR_TABLA_SHEETS.sql
```

### Paso 2: Verificar Tabla Creada

```sql
-- En Railway PostgreSQL
SELECT COUNT(*) FROM "Reservas_Con_Extras_Sheets";
```

### Paso 3: Verificar Sincronización

```bash
# Ver logs del monitor
railway logs --filter "Reservas → Sheets"
```

Deberías ver:
```
🔄 Monitor de Sincronización Reservas → Sheets inicializado
📊 Sincronizará los últimos 90 días cada 10 minutos
🔄 Sincronizando 384 reservas con Google Sheets...
✅ Sincronización completada: 384 reservas actualizadas
```

### Paso 4: Configurar hotboat-etl

Ver documentación de `hotboat-etl` para configurar la sincronización con Google Sheets.

## 🔧 Mantenimiento

### Ver Estado de Sincronización

```sql
-- Total de registros sincronizados
SELECT COUNT(*) as total_registros 
FROM "Reservas_Con_Extras_Sheets";

-- Última actualización
SELECT MAX(updated_at) as ultima_actualizacion 
FROM "Reservas_Con_Extras_Sheets";

-- Registros por mes
SELECT 
    DATE_TRUNC('month', (raw->>'fecha')::date) as mes,
    COUNT(*) as registros
FROM "Reservas_Con_Extras_Sheets"
GROUP BY mes
ORDER BY mes DESC;
```

### Forzar Resincronización

Si necesitas forzar una resincronización completa:

```sql
-- Vaciar tabla intermedia
TRUNCATE "Reservas_Con_Extras_Sheets";

-- El monitor la volverá a llenar en el próximo ciclo (10 min)
```

### Cambiar Rango de Sincronización

En `config.yaml`, ajusta `sync_days_back`:

```yaml
reservas_sheets_sync:
  sync_days_back: 180  # 6 meses en lugar de 90 días
```

## ❓ Troubleshooting

### Problema: No se sincronizan datos

**Verificar:**
1. ¿El monitor está habilitado en `config.yaml`?
2. ¿La tabla existe en Railway?
3. ¿Hay datos en `reservas_con_extras`?

```bash
railway run python -c "from app.config import get_settings, load_yaml_config; c = load_yaml_config(); print('Enabled:', c['monitors']['reservas_sheets_sync']['enabled'])"
```

### Problema: Datos desactualizados en Sheets

**Verificar:**
1. ¿`hotboat-etl` está corriendo?
2. ¿La configuración de Google Sheets API es correcta?
3. ¿Los permisos de la hoja son correctos?

### Problema: Tabla muy grande

**Solución:** Reducir `sync_days_back`:

```yaml
sync_days_back: 30  # Solo último mes
```

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs: `railway logs`
2. Verifica la tabla: `SELECT * FROM "Reservas_Con_Extras_Sheets" LIMIT 10;`
3. Confirma que `hotboat-etl` está configurado correctamente
