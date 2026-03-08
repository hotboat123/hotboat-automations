# Ejemplo Visual del Cruce de Tablas

Este documento muestra un ejemplo paso a paso de cómo se hace el cruce de tablas para generar el análisis consolidado de reservas.

## Datos de Entrada

### Tabla 1: booknetic_appointments

| id | start_date | customer | email | phone | service |
|----|------------|----------|-------|-------|---------|
| 458 | 11/01/2026 12:00 | Roxana Opazo | roxana@email.com | +56912345678 | HotBoat Trip 6 people |
| 459 | 11/01/2026 12:00 | Roxana Opazo | roxana@email.com | +56912345678 | HotBoat Trip 5 people |
| 607 | 11/01/2026 19:00 | Matias Levit | matias@email.com | +56987654321 | HotBoat Trip 2 people |

### Tabla 2: booknetic_payments

| id | appointment_date | payment | status | method |
|----|------------------|---------|--------|--------|
| 458 | 11/01/2026 12:00 | $0 | Paid (deposit) | Pay in Person |
| 459 | 11/01/2026 12:00 | $0 | Paid (deposit) | Pay in Person |
| 607 | 11/01/2026 19:00 | $0 | Paid (deposit) | WooCommerce |

### Tabla 3: Informacion Reservas

| id | fecha | horario_salida | nombre | cantidad_personas | extras |
|----|-------|----------------|--------|-------------------|--------|
| cc84c5ad | 11/01/2026 | 12:00:00 | Roxana Opazo | 6 | coca-cola: 1, cerveza_artesanal_negra: 8, champaña_riccadonna_moscato_rose: 1 |
| 00531ef7 | 11/01/2026 | 12:00:00 | Roxana Opazo | 5 | cerveza_artesanal_negra: 5, champaña_riccadonna_ruby: 1 |
| ae3356f6 | 11/01/2026 | 19:00:00 | Matias Levit | 2 | - |

## Paso 1: Normalizar las Fechas y Horas

```sql
-- appointments_data
458 → fecha: 2026-01-11, hora: 12:00:00, row_num: 1
459 → fecha: 2026-01-11, hora: 12:00:00, row_num: 2
607 → fecha: 2026-01-11, hora: 19:00:00, row_num: 1

-- payments_data
458 → fecha: 2026-01-11, hora: 12:00:00, row_num: 1
459 → fecha: 2026-01-11, hora: 12:00:00, row_num: 2
607 → fecha: 2026-01-11, hora: 19:00:00, row_num: 1

-- reservations_with_extras
cc84c5ad → fecha: 2026-01-11, hora: 12:00:00, row_num: 1
00531ef7 → fecha: 2026-01-11, hora: 12:00:00, row_num: 2
ae3356f6 → fecha: 2026-01-11, hora: 19:00:00, row_num: 1
```

## Paso 2: Hacer el Cruce (JOIN)

```
Reserva 1:
appointment[458] + payment[458] + info_reserva[cc84c5ad]
✓ fecha: 2026-01-11 = 2026-01-11 = 2026-01-11
✓ hora: 12:00:00 = 12:00:00 = 12:00:00
✓ row_num: 1 = 1 = 1

Reserva 2:
appointment[459] + payment[459] + info_reserva[00531ef7]
✓ fecha: 2026-01-11 = 2026-01-11 = 2026-01-11
✓ hora: 12:00:00 = 12:00:00 = 12:00:00
✓ row_num: 2 = 2 = 2

Reserva 3:
appointment[607] + payment[607] + info_reserva[ae3356f6]
✓ fecha: 2026-01-11 = 2026-01-11 = 2026-01-11
✓ hora: 19:00:00 = 19:00:00 = 19:00:00
✓ row_num: 1 = 1 = 1
```

## Paso 3: Procesar Extras

### Reserva 1 (cc84c5ad):
```python
extras_json = {
    'extras[Coca-cola]': '1',
    'extras[Cerveza Artesanal Negra]': '8',
    'extras[Champaña Riccadonna Moscato Rose]': '1'
}

# Calcular ingresos
coca_cola: 1 × 2900 = 2900
cerveza_artesanal_negra: 8 × 7900 = 63200
champaña_riccadonna_moscato_rose: 1 × 15000 = 15000
ingreso_extras = 81100

# Calcular costos
coca_cola: 1 × 750 = 750
cerveza_artesanal_negra: 8 × 3300 = 26400
champaña_riccadonna_moscato_rose: 1 × 7200 = 7200
costo_extras = 34350
```

### Reserva 2 (00531ef7):
```python
extras_json = {
    'extras[Cerveza Artesanal Negra]': '5',
    'extras[Champaña Riccadonna Ruby]': '1'
}

# Calcular ingresos
cerveza_artesanal_negra: 5 × 7900 = 39500
champaña_riccadonna_ruby: 1 × 15000 = 15000
ingreso_extras = 54500

# Calcular costos
cerveza_artesanal_negra: 5 × 3300 = 16500
champaña_riccadonna_ruby: 1 × 7200 = 7200
costo_extras = 23700
```

### Reserva 3 (ae3356f6):
```python
extras_json = {}

ingreso_extras = 0
costo_extras = 0
```

## Paso 4: Calcular Costos y Utilidades

### Reserva 1:
```python
# Ingresos
ingreso_reserva = 0  # Del payment
ingreso_extras = 81100
ingreso_total = 81100

# Costos
costo_fijo = 18000  # Gas (15k) + Leña (1k) + Agua (1k) + Hielo (1k)
costo_variable = 34350  # Costos de extras
costo_operativo = 52350
costo_marketing = 24067  # Del día 2026-01-11
costo_total = 76417

# Utilidades
utilidad_bruta = 81100 - 52350 = 28750
utilidad_neta = 81100 - 76417 = 4683
margen_bruto = (28750 / 81100) × 100 = 35.4%
margen_neto = (4683 / 81100) × 100 = 5.8%
```

### Reserva 2:
```python
# Ingresos
ingreso_reserva = 0
ingreso_extras = 54500
ingreso_total = 54500

# Costos
costo_fijo = 18000
costo_variable = 23700
costo_operativo = 41700
costo_marketing = 24067
costo_total = 65767

# Utilidades
utilidad_bruta = 54500 - 41700 = 12800
utilidad_neta = 54500 - 65767 = -11267
margen_bruto = (12800 / 54500) × 100 = 23.5%
margen_neto = (-11267 / 54500) × 100 = -20.7%
```

### Reserva 3:
```python
# Ingresos
ingreso_reserva = 0
ingreso_extras = 0
ingreso_total = 0

# Costos
costo_fijo = 18000
costo_variable = 0
costo_operativo = 18000
costo_marketing = 24067
costo_total = 42067

# Utilidades
utilidad_bruta = 0 - 18000 = -18000
utilidad_neta = 0 - 42067 = -42067
margen_bruto = 0%
margen_neto = 0%
```

## Resultado Final: CSV Consolidado

| Fecha | Hora | ID Appointment | ID Payment | ID Reserva | Nombre | Email | Ingreso Reserva | Ingreso Extras | Ingreso Total | Costo Op Total | Costo Marketing | Costo Total | Utilidad Neta | Margen Neto % | Extras |
|-------|------|----------------|------------|------------|--------|-------|----------------|---------------|---------------|---------------|----------------|-------------|--------------|--------------|--------|
| 11/01/2026 | 12:00 | 458 | 458 | cc84c5ad | Roxana Opazo | roxana@email.com | 0 | 81,100 | 81,100 | 52,350 | 24,067 | 76,417 | 4,683 | 5.8% | coca-cola x1, cerveza_artesanal_negra x8, champaña_riccadonna_moscato_rose x1 |
| 11/01/2026 | 12:00 | 459 | 459 | 00531ef7 | Roxana Opazo | roxana@email.com | 0 | 54,500 | 54,500 | 41,700 | 24,067 | 65,767 | -11,267 | -20.7% | cerveza_artesanal_negra x5, champaña_riccadonna_ruby x1 |
| 11/01/2026 | 19:00 | 607 | 607 | ae3356f6 | Matias Levit | matias@email.com | 0 | 0 | 0 | 18,000 | 24,067 | 42,067 | -42,067 | 0% | Sin extras |

## Resumen del Día

```
Total reservas: 3

INGRESOS:
  Reservas:        $       0
  Extras:          $ 135,600
  TOTAL:           $ 135,600

COSTOS:
  Operativos:      $ 112,050
  Marketing:       $  72,201  (24,067 × 3 reservas)
  TOTAL:           $ 184,251

UTILIDAD NETA:     $ -48,651
Margen Neto:         -35.9%
```

## Notas Importantes

1. **ROW_NUMBER es crucial**: Sin él, no podríamos diferenciar las dos reservas de Roxana a las 12:00
2. **Costo de marketing se repite**: Cada reserva carga con el costo de marketing del día completo
3. **Ingreso reserva = 0**: En este caso específico, porque los payments están en $0 (probablemente pagos en persona no registrados)
4. **Extras son la fuente principal de ingreso**: En este ejemplo, todo el ingreso viene de extras

## Scripts Relacionados

- `scripts/export_reservations_full.py` - Genera el CSV consolidado
- `scripts/export_daily_analysis.py` - Genera 3 CSVs (reservas, resumen diario, extras)
- `scripts/calculate_month_revenue_optimized.py` - Calcula ingresos del mes
