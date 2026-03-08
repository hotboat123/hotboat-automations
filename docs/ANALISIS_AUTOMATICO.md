# Análisis Automático de Reservas

Este script genera un análisis ejecutivo completo a partir del CSV de reservas consolidadas.

## 🚀 Uso Rápido

```bash
# Primero, exporta las reservas
python scripts/export_reservations_full.py 2026-01-01 2026-01-31

# Luego, genera el análisis
python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260131.csv
```

## 📊 ¿Qué Analiza?

El script genera automáticamente:

### 1. Resumen Ejecutivo
- Total de reservas
- Ingresos totales
- Costos totales
- Utilidad neta
- Margen neto

### 2. Problemas Identificados
- ⚠️ Ingreso por reserva = $0
- ⚠️ Costos de marketing elevados
- ⚠️ Baja tasa de conversión de extras
- ⚠️ Otras alertas automáticas

### 3. Análisis Financiero
- Desglose de ingresos (reservas vs extras)
- Desglose de costos (fijos, variables, marketing)
- Distribución de rentabilidad

### 4. Top 10 Clientes
- Clientes por ingreso total
- Número de reservas por cliente
- Ingreso promedio por cliente

### 5. Análisis de Extras
- Tasa de conversión (% que compra extras)
- Top 5 extras más mencionados
- Ingresos por extras

### 6. Análisis de Horarios
- Distribución de reservas por franja horaria
- Ingreso promedio por franja

### 7. Top 5 Reservas Más Rentables
- Detalle de las reservas con mejor margen
- Extras comprados
- Utilidad y margen de cada una

### 8. Recomendaciones Automáticas
- Acciones urgentes
- Optimizaciones de marketing
- Mejoras en extras

## 📁 Archivos Generados

El análisis se guarda como:
```
outputs/analisis_reservas_completas_YYYYMMDD_YYYYMMDD.md
```

Formato: **Markdown** (se puede abrir con cualquier editor de texto o visualizador de Markdown)

## 🔍 Ejemplo de Salida

```markdown
# Análisis de Reservas - Hot Boat

**Fecha de análisis:** 02/03/2026 22:54

## 📊 RESUMEN EJECUTIVO

- **Total Reservas:** 58
- **Ingreso Total:** $1,254,000
- **Costo Total:** $2,797,128
- **Utilidad Neta:** $-1,543,128
- **Margen Neto:** -123.1%

## 🚨 PROBLEMAS IDENTIFICADOS

### ⚠️ CRÍTICO: Ingreso por Reserva = $0
- TODAS las reservas tienen 'Ingreso Reserva' en $0
- Solo se capturan ingresos por extras
- **Acción requerida:** Revisar integración con sistema de pagos
...
```

## 🎯 Casos de Uso

### 1. Análisis Mensual
```bash
# Exportar enero
python scripts/export_reservations_full.py 2026-01-01 2026-01-31

# Analizar enero
python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260131.csv

# Ver el reporte
notepad outputs/analisis_reservas_completas_20260101_20260131.md
```

### 2. Comparar Meses
```bash
# Enero
python scripts/export_reservations_full.py 2026-01-01 2026-01-31
python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260131.csv

# Febrero
python scripts/export_reservations_full.py 2026-02-01 2026-02-28
python scripts/analizar_reservas.py outputs/reservas_completas_20260201_20260228.csv

# Comparar ambos reportes manualmente
```

### 3. Análisis Semanal
```bash
# Semana 1
python scripts/export_reservations_full.py 2026-01-01 2026-01-07
python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260107.csv

# Semana 2
python scripts/export_reservations_full.py 2026-01-08 2026-01-14
python scripts/analizar_reservas.py outputs/reservas_completas_20260108_20260114.csv
```

## 📈 Insights que Proporciona

### Problemas Detectados Automáticamente

El análisis identifica automáticamente:

✅ **Ingresos:**
- Si falta captura de ingreso base
- Si los extras son la única fuente de ingreso
- Si hay reservas sin ingresos

✅ **Costos:**
- Si el marketing es >40% de los costos
- Si el CAC (costo por adquisición) es >$15,000
- Si hay desbalance en la estructura de costos

✅ **Extras:**
- Si la tasa de conversión es <50%
- Cuáles extras se venden más
- Oportunidades de bundling

✅ **Rentabilidad:**
- Cuántas reservas son rentables vs no rentables
- Qué clientes son más valiosos
- Qué horarios son más rentables

## 🛠️ Personalización

Para agregar más análisis, edita `scripts/analizar_reservas.py`:

```python
def mi_analisis_custom(reservas: List[Dict]) -> Dict:
    """Tu análisis personalizado"""
    # ... tu código aquí
    return resultado
```

## 🔗 Workflow Completo

### Workflow Recomendado Mensual

```bash
# 1. Exportar datos del mes
python scripts/export_reservations_full.py 2026-01-01 2026-01-31

# 2. Generar análisis automático
python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260131.csv

# 3. Revisar el reporte en Markdown
# outputs/analisis_reservas_completas_20260101_20260131.md

# 4. (Opcional) Generar análisis detallado con 3 CSVs
python scripts/export_daily_analysis.py 2026-01-01 2026-01-31
```

### Archivos Generados

```
outputs/
├── reservas_completas_20260101_20260131.csv       ← CSV consolidado
├── analisis_reservas_completas_20260101_20260131.md  ← Análisis automático
├── analisis_reservas_20260101_20260131.csv        ← (Opcional) Detallado
├── resumen_diario_20260101_20260131.csv           ← (Opcional) Por día
└── resumen_extras_20260101_20260131.csv           ← (Opcional) Extras
```

## 💡 Tips

### 1. Ver el Markdown Formateado

**En VS Code:**
- Abre el archivo `.md`
- Presiona `Ctrl+Shift+V` (Preview)

**En GitHub:**
- Sube el archivo `.md` al repo
- GitHub lo muestra formateado automáticamente

**Online:**
- Sube a https://dillinger.io/
- Copia y pega el contenido

### 2. Convertir a PDF

```bash
# Instalar pandoc
# Windows: choco install pandoc
# Mac: brew install pandoc
# Linux: apt-get install pandoc

# Convertir
pandoc outputs/analisis_reservas_completas_20260101_20260131.md -o reporte.pdf
```

### 3. Convertir a HTML

```bash
pandoc outputs/analisis_reservas_completas_20260101_20260131.md -o reporte.html
```

## 🚨 Errores Comunes

### "File not found"
Asegúrate de que el CSV existe:
```bash
dir outputs\reservas_completas_*.csv
```

### "Invalid CSV"
Verifica que el CSV tenga el formato correcto (generado por `export_reservations_full.py`)

### "Encoding error"
El script espera UTF-8-BOM. Si exportaste el CSV con otro programa, asegúrate del encoding.

## 📊 Métricas Clave

El análisis calcula automáticamente:

| Métrica | Descripción |
|---------|-------------|
| **Margen Neto** | (Utilidad / Ingreso) × 100 |
| **CAC** | Costo Marketing / Reservas |
| **Tasa Conversión Extras** | (Con Extras / Total) × 100 |
| **Ticket Promedio** | Ingreso Total / Reservas |
| **Rentabilidad** | Reservas Rentables / Total |

## 🔄 Automatización

Para ejecutar automáticamente cada mes:

### Windows (Task Scheduler)
```batch
@echo off
set MES=2026-01
python scripts/export_reservations_full.py %MES%-01 %MES%-31
python scripts/analizar_reservas.py outputs/reservas_completas_%MES%01_%MES%31.csv
```

### Linux/Mac (Cron)
```bash
# Ejecutar el primer día de cada mes a las 9 AM
0 9 1 * * cd /path/to/hotboat-automations && ./scripts/monthly_analysis.sh
```

## 📝 Próximas Mejoras

- [ ] Gráficos automáticos (matplotlib)
- [ ] Comparación mes a mes
- [ ] Predicciones con ML
- [ ] Export a Excel con formato
- [ ] Dashboard interactivo
- [ ] Alertas automáticas por email

## 🤝 Contribuir

Para agregar más análisis:
1. Edita `scripts/analizar_reservas.py`
2. Agrega tu función de análisis
3. Llama desde `generar_reporte()`
4. Agrega al template de Markdown

## Ver También

- [EXPORT_RESERVATIONS.md](../docs/EXPORT_RESERVATIONS.md) - Exportar CSV consolidado
- [CRUCE_TABLAS.md](../docs/CRUCE_TABLAS.md) - Cómo funciona el cruce
- [EJEMPLO_CRUCE_TABLAS.md](../docs/EJEMPLO_CRUCE_TABLAS.md) - Ejemplo visual
