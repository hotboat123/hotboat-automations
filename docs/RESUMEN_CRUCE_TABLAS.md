# Resumen: Sistema de Cruce de Tablas y Exportación de Reservas

## ¿Qué se Implementó?

### 1. Script de Exportación Completo (`export_reservations_full.py`)

Script que genera un CSV consolidado con **toda la información** de cada reserva, cruzando 3 tablas:

- ✅ `booknetic_appointments` (datos de citas)
- ✅ `booknetic_payments` (datos de pagos)  
- ✅ `Informacion Reservas` (extras y detalles)

**Características:**
- Cruce inteligente por fecha + hora + ROW_NUMBER
- Cálculo automático de ingresos, costos y utilidades
- Análisis de márgenes de utilidad (bruto y neto)
- Incluye costos de marketing por día
- Exportación a CSV con encoding UTF-8-BOM (compatible con Excel)

### 2. Scripts de Ejecución Rápida

- ✅ `export_reservations.bat` (Windows)
- ✅ `export_reservations.sh` (Linux/Mac)

### 3. Documentación Completa

- ✅ `docs/CRUCE_TABLAS.md` - Explicación técnica del cruce
- ✅ `docs/EXPORT_RESERVATIONS.md` - Guía de uso completa
- ✅ `docs/EJEMPLO_CRUCE_TABLAS.md` - Ejemplo visual paso a paso
- ✅ `README.md` actualizado con nueva sección

## ¿Cómo Funciona el Cruce?

### Criterios de Cruce (JOIN)

El sistema une las 3 tablas usando **3 criterios**:

1. **Fecha**: Misma fecha de reserva
   ```sql
   DATE(appointments.start_date) = DATE(info_reservas.fecha)
   ```

2. **Hora**: Misma hora de salida  
   ```sql
   TO_CHAR(appointments.start_date, 'HH24:MI:SS') = info_reservas.horario_salida
   ```

3. **ROW_NUMBER**: Para múltiples reservas en la misma fecha/hora
   ```sql
   ROW_NUMBER() OVER (PARTITION BY fecha, hora ORDER BY id) = 
   ROW_NUMBER() OVER (PARTITION BY fecha, hora ORDER BY created_at)
   ```

### Ejemplo Visual

```
Reserva a las 12:00 (1ª) + Payment a las 12:00 (1º) + Info Reserva a las 12:00 (1ª)
     ✓ fecha            ✓ hora              ✓ row_num
```

## Columnas del CSV Generado

### Identificadores
- Fecha, Hora
- ID Appointment, ID Payment, ID Reserva

### Información del Cliente
- Nombre Cliente, Email, Teléfono

### Detalles de la Reserva
- Servicio, Ubicación, Num Personas, Descuento %, Notas

### Ingresos
- Ingreso Reserva
- Ingreso Extras
- Ingreso Total

### Costos
- Costo Op Fijo (gas, leña, agua, hielo = $18.000)
- Costo Op Variable (costos de extras)
- Costo Op Total
- Costo Marketing
- Costo Total

### Utilidades
- Utilidad Bruta (ingreso - costo operativo)
- Utilidad Neta (ingreso - costo total)
- Margen Bruto %
- Margen Neto %

### Otros
- Extras (lista de extras vendidos)
- Status Appointment, Status Payment, Método Pago
- Timestamps de creación

## Uso Rápido

### Windows
```bash
# Un día
export_reservations.bat 2026-01-01

# Rango de fechas
export_reservations.bat 2026-01-01 2026-01-31
```

### Linux/Mac
```bash
# Un día
./export_reservations.sh 2026-01-01

# Rango de fechas
./export_reservations.sh 2026-01-01 2026-01-31
```

### Python directo
```bash
python scripts/export_reservations_full.py 2026-01-01 2026-01-31
```

## Salida del Script

```
================================================================================
EXPORTANDO INFORMACIÓN COMPLETA DE RESERVAS
================================================================================

Periodo: 01/01/2026 - 31/01/2026

Cargando costos y precios desde base de datos...
[OK] Costos cargados: 52 extras
[OK] Precios cargados: 52 extras

Cargando costos de marketing...
[OK] Costos de marketing cargados para 27 días

Obteniendo información consolidada de reservas...
[OK] Reservas encontradas: 58

Generando archivo CSV...

================================================================================
RESUMEN
================================================================================
Total reservas:          58

INGRESOS:
  Reservas:              $   2,250,000
  Extras:                $   1,254,000
  ---------------------------------
  TOTAL INGRESOS:        $   3,504,000

COSTOS:
  Operativos + Marketing:$   2,797,128

UTILIDAD:
  Utilidad Neta:         $     706,872
  Margen Neto:                   20.2%

Promedio por reserva:    $      60,414

================================================================================
ARCHIVO GENERADO
================================================================================
C:\Users\...\outputs\reservas_completas_20260101_20260131.csv

[OK] Archivo CSV generado exitosamente con 58 reservas
================================================================================
```

## Ubicación del Archivo

El CSV se guarda en `outputs/` con formato:
- Un día: `reservas_completas_20260101.csv`
- Rango: `reservas_completas_20260101_20260131.csv`

## Casos de Uso

### 1. Análisis de Rentabilidad por Reserva
Ver qué reservas son más rentables y cuáles no

### 2. Análisis de Extras
Identificar qué extras se venden más y su contribución al ingreso

### 3. Impacto del Marketing
Ver cómo los costos de marketing afectan la utilidad neta

### 4. Análisis de Clientes
Identificar clientes frecuentes y su comportamiento de compra

### 5. Reportes Contables
Tener un registro detallado de todas las transacciones

## Scripts Relacionados

| Script | Descripción |
|--------|-------------|
| `export_reservations_full.py` | 📊 CSV consolidado con toda la información |
| `export_daily_analysis.py` | 📈 3 CSVs (reservas, resumen diario, extras) |
| `calculate_month_revenue_optimized.py` | 💰 Cálculo de ingresos del mes |
| `calculate_daily_revenue.py` | 📅 Cálculo de ingresos de un día |

## Archivos Creados

```
hotboat-automations/
├── scripts/
│   └── export_reservations_full.py        ← Script principal
├── docs/
│   ├── CRUCE_TABLAS.md                   ← Explicación técnica
│   ├── EXPORT_RESERVATIONS.md            ← Guía de uso
│   ├── EJEMPLO_CRUCE_TABLAS.md           ← Ejemplo visual
│   └── RESUMEN_CRUCE_TABLAS.md           ← Este archivo
├── outputs/
│   └── reservas_completas_*.csv          ← CSVs generados
├── export_reservations.bat               ← Script Windows
├── export_reservations.sh                ← Script Linux/Mac
└── README.md                             ← Actualizado con nueva sección
```

## Documentación Disponible

1. **CRUCE_TABLAS.md**: Explicación técnica detallada del cruce con queries SQL
2. **EXPORT_RESERVATIONS.md**: Guía completa de uso del script
3. **EJEMPLO_CRUCE_TABLAS.md**: Ejemplo visual paso a paso con datos reales
4. **README.md**: Sección de "Análisis y Reportes" agregada

## Ventajas de esta Implementación

✅ **Consolidación automática**: No hay que hacer cruces manuales  
✅ **Cálculos precisos**: Costos y utilidades calculados correctamente  
✅ **Fácil de usar**: Scripts de ejecución con un solo comando  
✅ **Compatible con Excel**: Encoding UTF-8-BOM  
✅ **Documentación completa**: Ejemplos y guías detalladas  
✅ **Flexible**: Funciona para un día o rango de fechas  
✅ **Completo**: Incluye toda la información disponible  

## Próximos Pasos Recomendados

1. **Automatizar**: Crear un cron job para generar el CSV diariamente
2. **Dashboard**: Usar los datos para crear un dashboard en Google Sheets o Power BI
3. **Alertas**: Configurar alertas cuando el margen neto baje de cierto umbral
4. **Análisis predictivo**: Usar los datos históricos para predecir ventas futuras

## Soporte

Para más información, consulta:
- `docs/CRUCE_TABLAS.md` - Detalles técnicos
- `docs/EXPORT_RESERVATIONS.md` - Guía de uso
- `docs/EJEMPLO_CRUCE_TABLAS.md` - Ejemplo visual
