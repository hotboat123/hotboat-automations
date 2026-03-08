# Exportar Información Completa de Reservas

Este script genera un CSV consolidado con **toda la información** de cada reserva, incluyendo datos de appointments, payments, información de reservas, extras, costos y utilidades.

## Características

✅ **Información consolidada** de 3 tablas (appointments, payments, Informacion Reservas)  
✅ **Cálculo automático** de ingresos, costos y utilidades  
✅ **Análisis de extras** con precios y costos  
✅ **Costos de marketing** incluidos por día  
✅ **Márgenes de utilidad** (bruto y neto)  
✅ **Exportación a CSV** con encoding UTF-8-BOM (compatible con Excel)

## Uso Rápido

### Windows
```bash
# Un día específico
export_reservations.bat 2026-01-01

# Rango de fechas
export_reservations.bat 2026-01-01 2026-01-31
```

### Linux/Mac
```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x export_reservations.sh

# Un día específico
./export_reservations.sh 2026-01-01

# Rango de fechas
./export_reservations.sh 2026-01-01 2026-01-31
```

### Directamente con Python
```bash
python scripts/export_reservations_full.py 2026-01-01 2026-01-31
```

## Columnas del CSV Generado

### Identificadores
- `Fecha`: Fecha de la reserva (DD/MM/YYYY)
- `Hora`: Hora de salida (HH:MM)
- `ID Appointment`: ID de la cita (primeros 8 caracteres)
- `ID Payment`: ID del pago (primeros 8 caracteres)
- `ID Reserva`: ID de Información Reservas (primeros 8 caracteres)

### Información del Cliente
- `Nombre Cliente`: Nombre completo
- `Email`: Email de contacto
- `Telefono`: Teléfono de contacto

### Detalles de la Reserva
- `Servicio`: Nombre del servicio contratado
- `Ubicacion`: Ubicación de la reserva
- `Num Personas`: Cantidad de personas
- `Descuento %`: Porcentaje de descuento aplicado
- `Notas`: Notas adicionales

### Ingresos
- `Ingreso Reserva`: Ingreso por la reserva base
- `Ingreso Extras`: Ingreso por extras vendidos
- `Ingreso Total`: Total de ingresos (reserva + extras)

### Costos
- `Costo Op Fijo`: Costos operativos fijos (gas, leña, agua, hielo = $18.000)
- `Costo Op Variable`: Costos variables (costos de los extras vendidos)
- `Costo Op Total`: Total costos operativos (fijos + variables)
- `Costo Marketing`: Costo de marketing asignado a ese día
- `Costo Total`: Total de costos (operativos + marketing)

### Utilidades y Márgenes
- `Utilidad Bruta`: Ingreso Total - Costo Operativo Total
- `Utilidad Neta`: Ingreso Total - Costo Total (incluyendo marketing)
- `Margen Bruto %`: (Utilidad Bruta / Ingreso Total) × 100
- `Margen Neto %`: (Utilidad Neta / Ingreso Total) × 100

### Extras
- `Extras`: Lista de extras vendidos (formato: "nombre x cantidad, ...")

### Status y Timestamps
- `Status Appointment`: Estado de la cita
- `Status Payment`: Estado del pago
- `Metodo Pago`: Método de pago utilizado
- `Creado Appointment`: Fecha de creación de la cita
- `Creado Info Reserva`: Fecha de creación de la información de reserva

## Ejemplo de Salida

```csv
Fecha,Hora,ID Appointment,ID Payment,ID Reserva,Nombre Cliente,Email,Telefono,Servicio,Ubicacion,Num Personas,Descuento %,Notas,Ingreso Reserva,Ingreso Extras,Ingreso Total,Costo Op Fijo,Costo Op Variable,Costo Op Total,Costo Marketing,Costo Total,Utilidad Bruta,Utilidad Neta,Margen Bruto %,Margen Neto %,Extras,Status Appointment,Status Payment,Metodo Pago,Creado Appointment,Creado Info Reserva
01/01/2026,10:00,abc12345,def67890,ghi01234,Juan Pérez,juan@email.com,+573001234567,Tour Privado,Lago,6,0.0,Cliente VIP,150000,65000,215000,18000,32000,50000,8500,58500,165000,156500,76.7,72.8,"Cerveza Corona x6, Tabla 2 personas x1",confirmed,paid,online,01/01/2026 08:30,01/01/2026 08:35
```

## Resumen en Consola

Al ejecutar el script, verás un resumen:

```
================================================================================
RESUMEN
================================================================================
Total reservas:          15

INGRESOS:
  Reservas:              $  2,250,000
  Extras:                $    975,000
  ─────────────────────────────────
  TOTAL INGRESOS:        $  3,225,000

COSTOS:
  Operativos + Marketing:$    895,000

UTILIDAD:
  Utilidad Neta:         $  2,330,000
  Margen Neto:                 72.2%

Promedio por reserva:    $    215,000

================================================================================
ARCHIVO GENERADO
================================================================================
📄 c:\Users\cuent\Desktop\hotboat-automations\outputs\reservas_completas_20260101_20260131.csv

✓ Archivo CSV generado exitosamente con 15 reservas
================================================================================
```

## Ubicación del Archivo

El CSV se guarda en la carpeta `outputs/` con el siguiente formato:

- **Un día:** `reservas_completas_YYYYMMDD.csv`
- **Rango:** `reservas_completas_YYYYMMDD_YYYYMMDD.csv`

Ejemplos:
- `outputs/reservas_completas_20260101.csv`
- `outputs/reservas_completas_20260101_20260131.csv`

## Cómo Funciona el Cruce de Tablas

El script hace un cruce (JOIN) de 3 tablas usando:

1. **Fecha**: Misma fecha de reserva
2. **Hora**: Misma hora de salida
3. **ROW_NUMBER**: Para emparejar múltiples reservas en la misma fecha/hora

Para más detalles técnicos, consulta: [docs/CRUCE_TABLAS.md](docs/CRUCE_TABLAS.md)

## Requisitos

- Python 3.10+
- PostgreSQL con las tablas configuradas
- Variables de entorno configuradas (DATABASE_URL)
- Paquetes instalados: `psycopg`, `python-dotenv`

## Errores Comunes

### "Error: Formato de fecha inválido"
Asegúrate de usar el formato `YYYY-MM-DD`:
```bash
# ❌ Incorrecto
export_reservations.bat 01/01/2026

# ✅ Correcto
export_reservations.bat 2026-01-01
```

### "No se encontraron reservas"
Verifica que:
- Las fechas están en el rango correcto
- Hay datos en la base de datos para ese período
- La conexión a la base de datos está funcionando

### "Module not found"
Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Scripts Relacionados

- `export_daily_analysis.py`: Análisis detallado con 3 CSVs (reservas, resumen diario, resumen extras)
- `calculate_month_revenue_optimized.py`: Cálculo de ingresos del mes
- `review_date_report.py`: Reporte de una fecha específica

## Ver También

- [CRUCE_TABLAS.md](docs/CRUCE_TABLAS.md) - Explicación técnica del cruce de tablas
- [MARKETING_COSTS.md](docs/MARKETING_COSTS.md) - Gestión de costos de marketing
- [EXAMPLES.md](EXAMPLES.md) - Más ejemplos de uso
