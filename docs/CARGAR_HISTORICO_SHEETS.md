# Cargar Datos Históricos a Google Sheets

## Problema
La tabla `Reservas_Con_Extras_Sheets` solo tiene datos desde enero 2026. Necesitamos cargar TODOS los datos históricos.

## Solución

### Paso 1: Ejecutar en Railway

Accede a Railway y ejecuta el siguiente comando en la terminal del proyecto:

```bash
railway run python scripts/sync_all_historical_data.py
```

Este script:
1. Consulta TODAS las reservas de `reservas_con_extras` (sin filtro de fecha)
2. Por cada reserva, verifica si ya existe en `Reservas_Con_Extras_Sheets`
3. Si existe, actualiza el registro
4. Si no existe, lo inserta
5. Muestra progreso cada 50 registros

### Paso 2: Verificar resultados

Después de ejecutar el script, verifica cuántos registros se cargaron:

```sql
SELECT 
    COUNT(*) as total_registros,
    MIN(raw->>'fecha') as fecha_mas_antigua,
    MAX(raw->>'fecha') as fecha_mas_reciente
FROM "Reservas_Con_Extras_Sheets";
```

### Paso 3: Confirmar en Google Sheets

Una vez que `hotboat-etl` sincronice los datos, deberías ver toda la información histórica en tu Google Sheet.

## Comportamiento futuro

Después de esta carga inicial:
- El monitor `reservas_sheets_sync` sincroniza automáticamente cada 10 minutos
- **Solo sincroniza fechas >= HOY** para no modificar tus ediciones manuales
- Los datos históricos (fechas pasadas) quedan intactos

## Si necesitas re-sincronizar fechas pasadas

Solo en caso de necesitar corregir/actualizar datos históricos:

1. Edita `config.yaml`:
```yaml
reservas_sheets_sync:
  sync_from_today: false  # Temporalmente sincroniza todo
```

2. Commit y push
3. Espera 10 minutos o reinicia el servicio en Railway
4. Vuelve a activar `sync_from_today: true`

## Notas importantes

- ✅ Este script es seguro: usa UPSERT (update si existe, insert si no)
- ✅ Preserva datos existentes al hacer UPDATE
- ✅ Se puede ejecutar múltiples veces sin duplicar registros
- ⚠️ Puede tardar varios minutos si hay muchas reservas
