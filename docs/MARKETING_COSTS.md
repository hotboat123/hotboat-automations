# Sistema de Costos de Marketing y Utilidad Operativa

Este documento explica cómo funciona el sistema de seguimiento de costos de marketing y cálculo de utilidad operativa.

## 📋 Descripción General

El sistema integra los costos de marketing (Meta/Facebook Ads) con los ingresos diarios para calcular la **utilidad operativa** del negocio. Esto permite ver día a día cuánto se gana después de restar los gastos en publicidad.

### Fórmula de Utilidad Operativa:
```
Utilidad Operativa = Ingresos Totales - Costos de Marketing

Margen de Utilidad = (Utilidad Operativa / Ingresos Totales) × 100%
```

## 🗄️ Base de Datos

### Tabla `marketing_costs`

Almacena los costos diarios de marketing:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | ID único |
| `cost_date` | DATE | Fecha del gasto |
| `ad_name` | TEXT | Nombre del anuncio |
| `campaign_name` | TEXT | Nombre de la campaña |
| `adset_name` | TEXT | Nombre del conjunto de anuncios |
| `amount_spent` | NUMERIC | Monto gastado en CLP |
| `currency` | TEXT | Moneda (CLP) |
| `reach` | INTEGER | Alcance |
| `impressions` | INTEGER | Impresiones |
| `clicks` | INTEGER | Clicks |
| `purchases` | INTEGER | Compras |
| `raw` | JSONB | Datos completos del CSV |

### Vista `marketing_costs_daily`

Vista agregada que resume los costos por día:
- Total gastado
- Número de anuncios
- Métricas agregadas (alcance, impresiones, clicks, compras)
- CPC promedio
- Costo por compra

## 📥 Importar Datos de Marketing

### 1. Exportar desde Meta Business Suite

1. Ve a Meta Business Suite → Administrador de anuncios
2. Selecciona el período que deseas exportar
3. Exporta como CSV con las siguientes columnas:
   - Nombre del anuncio
   - Día
   - Nombre de la campaña
   - Nombre del conjunto de anuncios
   - Importe gastado (CLP)
   - Alcance, Impresiones, Clics, Compras, etc.

### 2. Importar el CSV

#### Opción A: Método Simple (Recomendado) 🎯

1. Guarda tu CSV exportado en: `inputs/marketing/marketing_costs.csv`
2. Ejecuta:
```bash
python scripts/update_marketing.py
```

Este script:
- ✅ Busca automáticamente el archivo en la carpeta `inputs/`
- ✅ Te pide confirmación antes de actualizar
- ✅ Reemplaza los datos existentes
- ✅ Muestra un resumen de lo importado

#### Opción B: Método Manual

```bash
# Primera importación
python scripts/import_marketing_costs.py "ruta/al/archivo.csv"

# Actualizar datos (reemplaza los existentes)
python scripts/import_marketing_costs.py "ruta/al/archivo.csv" --replace
```

El script:
- ✅ Valida los datos del CSV
- ✅ Muestra un resumen antes de importar
- ✅ Inserta los datos en la base de datos
- ✅ Muestra un resumen por día

### 3. Verificar Datos Importados

```bash
python scripts/simple_verify_marketing.py
```

Muestra:
- Total de registros importados
- Datos de una fecha específica
- Resumen semanal

## 📊 Reportes

### Reporte Diario

Se envía automáticamente a las 9:00 AM e incluye:

```
💰 INGRESOS DEL DÍA
💵 Total Reservas: $XXX,XXX
🍾 Total Extras: $XX,XXX
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: $XXX,XXX

📢 COSTOS DE MARKETING
💸 Gasto en marketing: $XX,XXX
📱 Anuncios activos: X

📈 UTILIDAD OPERATIVA
💰 Ingresos: $XXX,XXX
📢 Marketing: -$XX,XXX
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD: $XXX,XXX
📊 Margen: XX.X%
```

**Generar manualmente:**
```bash
python scripts/review_date_report.py 2026-01-18
```

### Reporte Semanal

Se envía automáticamente los lunes a las 9:00 AM.

**Generar manualmente:**
```bash
# Última semana completa
python scripts/test_weekly_monthly_report.py weekly

# Semana actual (en progreso)
python scripts/test_weekly_monthly_report.py weekly current
```

Incluye:
- Resumen de operaciones
- Ingresos y extras
- **Costos totales de marketing**
- **Utilidad operativa total**
- **Margen de utilidad**
- Detalle por día (con marketing y utilidad de cada día)
- Top 5 días con mejores ingresos

### Reporte Mensual

Se envía automáticamente el primer lunes de cada mes.

**Generar manualmente:**
```bash
# Mes anterior completo
python scripts/test_weekly_monthly_report.py monthly

# Mes actual (en progreso)
python scripts/test_weekly_monthly_report.py monthly current
```

## 🔄 Actualización de Datos

### Frecuencia Recomendada

- **Diaria**: Exporta y actualiza los datos cada mañana antes de las 9:00 AM para que el reporte diario incluya los costos más recientes.
- **Semanal**: Al menos una vez por semana, especialmente antes del reporte semanal del lunes.
- **Mensual**: Al inicio de cada mes para cerrar los datos del mes anterior.

### Proceso Sugerido (Método Simple)

1. Descargar CSV actualizado de Meta Business Suite
2. Guardarlo como `marketing_costs.csv` en la carpeta `inputs/marketing/` (reemplazando el anterior)
3. Ejecutar actualización:
   ```bash
   python scripts/update_marketing.py
   ```
4. Confirmar cuando el script pregunte
5. ¡Listo! Los datos están actualizados

### Proceso Alternativo (Método Manual)

1. Descargar CSV actualizado de Meta Business Suite
2. Guardar con nombre descriptivo (ej: `marketing_2026-01-25.csv`)
3. Ejecutar importación:
   ```bash
   python scripts/import_marketing_costs.py "C:\ruta\marketing_2026-01-25.csv" --replace
   ```
4. Verificar datos:
   ```bash
   python scripts/simple_verify_marketing.py
   ```

## 📈 Análisis de Utilidad

### Interpretación de Métricas

**Margen de Utilidad Saludable:**
- ✅ **> 50%**: Excelente - Marketing muy eficiente
- ⚠️ **30-50%**: Bueno - Rango normal para eCommerce
- ❌ **< 30%**: Bajo - Considerar optimizar campañas

**Indicadores de Alerta:**
- Margen negativo (utilidad negativa) → Marketing más caro que los ingresos
- Margen decreciente → Aumentan costos sin aumentar ventas proporcionalmente
- Días con alta inversión pero pocas reservas → Campañas ineficientes

### Optimización

El sistema te permite:
1. Identificar días con mejor ROI (retorno de inversión)
2. Comparar campañas efectivas vs. ineficientes
3. Ajustar presupuestos según rendimiento
4. Tomar decisiones basadas en datos reales

## 🛠️ Archivos Importantes

- `app/monitors/daily_summary_monitor.py` - Calcula ingresos y utilidad diaria
- `app/monitors/weekly_monthly_summary_monitor.py` - Genera reportes semanales/mensuales
- `scripts/import_marketing_costs.py` - Importa datos de marketing
- `scripts/simple_verify_marketing.py` - Verifica datos importados
- `migrations/004_create_marketing_costs.sql` - Estructura de base de datos

## 💡 Tips

1. **Mantén el CSV actualizado**: Los reportes son tan precisos como los datos que importas.
2. **Revisa semanalmente**: Compara tu utilidad semana a semana para detectar tendencias.
3. **Exporta con todas las columnas**: Aunque no todas se usan, tenerlas en `raw` permite análisis futuros.
4. **Usa el flag `--replace`**: Al actualizar datos, siempre usa `--replace` para evitar duplicados.

## 🚀 Próximos Pasos (Futuro)

- Dashboard web con gráficos interactivos
- Alertas automáticas cuando el margen baja de cierto umbral
- Comparación de campañas específicas
- Predicción de utilidad basada en tendencias
- Integración directa con Meta API (sin necesidad de CSV)

---

**Última actualización**: Enero 2026
