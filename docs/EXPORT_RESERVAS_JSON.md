# Exportar Reservas con Extras en Formato JSON

Script mejorado que exporta reservas con el **cruce correcto** de datos y extras en formato diccionario JSON.

## 🎯 ¿Qué Hace Este Script?

Genera **2 archivos CSV**:

### 1. `reservas_extras_YYYYMMDD_YYYYMMDD.csv`
Todas las reservas (appointments) con sus extras en formato JSON.

**Columnas (en orden):**

1. **Fecha** - Fecha de la reserva (DD/MM/YYYY)
2. **Hora** - Hora de inicio (HH:MM)
3. **Nombre Cliente** - Nombre completo del cliente
4. **Servicio** - Servicio contratado
5. **Ingreso Reserva** - Ingreso base (captura correctamente el valor)
6. **Ingreso Extras** - Ingreso adicional por extras
7. **Ingreso Total** - Suma de Reserva + Extras
8. **Costo Operativo Fijo** - Costo fijo por reserva
9. **Costo Operativo Variable** - Suma de costos de extras
10. **Costo Operativo Total** - Costo fijo + variable
11. **Num Adultos** - Número de adultos en la reserva
12. **Num Ninos** - Número de niños en la reserva
13. **Ciudad Origen** - Ciudad de donde viene el cliente
14. **Como Supieron** - Cómo se enteraron de HotBoat (Instagram, TV, etc.)
15. **Clima del Dia** - Condición climática (Sol, Lluvia, Nublado, etc.)
16. **Tipo Clientes** - Tipo (Trabajador, Empresario, Estudiante, etc.)
17. **ID Appointment** - ID único del appointment (8 caracteres)
18. **ID Reserva** - ID único de Info Reserva (8 caracteres)

**Columnas adicionales** (al final):
- Email, Teléfono, Num Personas
- Categoria Clientes (Pareja, Familia, Grupo de amigos, etc.)
- Status
- **Extras (JSON)** - Diccionario con formato: `{"extra": cantidad, ...}`
- **Tiene Cruce** - Si/No (indica si se cruzó con "Informacion Reservas")

### 2. `reservas_extras_YYYYMMDD_YYYYMMDD_huerfanas.csv`
Registros de "Informacion Reservas" que **NO** se cruzaron con ningún appointment.

**Columnas:**
- ID Reserva
- Fecha, Hora
- Nombre, Teléfono, Email
- Num Personas
- **Num Adultos** - Número de adultos en la reserva
- **Num Ninos** - Número de niños en la reserva
- Ingreso Extras, Costo Extras
- **Extras (JSON)**
- Creado
- Motivo (por qué no se cruzó)

## 🚀 Uso Rápido

### Windows
```bash
export_reservas_extras.bat 2026-01-01 2026-01-31
```

### Linux/Mac
```bash
chmod +x export_reservas_extras.sh
./export_reservas_extras.sh 2026-01-01 2026-01-31
```

### Python Directo
```bash
python scripts/export_reservas_con_extras.py 2026-01-01 2026-01-31
```

## 📊 Ejemplo de Salida

### CSV de Reservas Cruzadas

```csv
Fecha,Hora,ID Appointment,ID Reserva,Nombre Cliente,Ciudad Origen,Como Supieron,Clima del Dia,Categoria Clientes,Tipo Clientes,Ingreso Reserva,Ingreso Extras,Ingreso Total,Extras (JSON),Tiene Cruce
01/01/2026,15:00,578,0b14554e,Rossana Balboa Soto,Concepcion,Instagram,Sol,Familia,Trabajador,194950,14500,209450,"{""fanta"": 1, ""coca-cola"": 4}",Si
01/01/2026,18:00,517,f8d8ea33,Florencia Crisoliti,Argentina,Instagram,,Familia,Empresario,204960,37000,241960,"{""cerveza_royal"": 3, ""tabla_4_personas"": 1}",Si
02/01/2026,12:00,581,235c194a,MARYORI VARGAS,Concepcion,Instagram,Sol,Familia,Trabajador,179960,5800,185760,"{""coca-cola"": 2}",Si
02/01/2026,20:00,573,b2d22614,Ignacio Vatel,Santiago,Instagram,Sol,Pareja,Empresario,139980,0,139980,{},Si
```

### CSV de Huérfanas (Sin Cruce)

```csv
ID Reserva,Fecha,Hora,Nombre,Num Adultos,Num Ninos,Ingreso Extras,Extras (JSON),Motivo
ec492652,10/01/2026,11:00:00,Sin nombre,2,0,38400,"{""fanta"": 1, ""tabla_2_personas"": 1}",No se encontro appointment con misma fecha/hora
8dcc36ec,26/01/2026,18:30:00,Sin nombre,2,0,20000,"{""tabla_2_personas"": 1}",No se encontro appointment con misma fecha/hora
```

## 🔍 Diferencias con el Script Anterior

| Aspecto | Script Anterior (`export_reservations_full.py`) | Script Nuevo (`export_reservas_con_extras.py`) |
|---------|------------------------------------------------|------------------------------------------------|
| **Fuente Principal** | booknetic_payments | booknetic_appointments |
| **Ingreso Reserva** | ❌ Siempre $0 | ✅ Captura correctamente |
| **Formato Extras** | String: "extra x1, extra x2" | JSON: `{"extra": 1, "extra2": 2}` |
| **Huérfanas** | ❌ No incluye | ✅ CSV separado |
| **Cruce** | payments + appointments + info | appointments + info |

## 📈 Resultados del Análisis Enero 2026

Usando el nuevo script:

```
Total reservas:                58
  - Con cruce a Info Reservas:  44 (75.9%)
  - Sin cruce a Info Reservas:  14 (24.1%)

Info Reservas huerfanas:       9

Ingreso total:                 $10,819,024
Ingreso por extras:            $1,254,000
Porcentaje extras:             11.6%
```

### ✅ Ahora Sí Captura los Ingresos Base

- **Antes:** $0 en todas las reservas
- **Ahora:** $10,819,024 total (con extras $1,254,000)

## 🎯 Formato JSON de Extras

Los extras ahora están en formato JSON válido que puedes:

### 1. Parsear en Excel/Python
```python
import json
import pandas as pd

df = pd.read_csv('reservas_extras_20260101_20260131.csv')

# Parsear JSON
df['extras_dict'] = df['Extras (JSON)'].apply(json.loads)

# Ver un ejemplo
print(df.iloc[0]['extras_dict'])
# Output: {'fanta': 1, 'coca-cola': 4}
```

### 2. Usar en SQL/PostgreSQL
```sql
-- Si importas el CSV a PostgreSQL
SELECT 
    nombre_cliente,
    (extras_json::json->>'tabla_2_personas')::int as tabla_2
FROM reservas
WHERE extras_json::json ? 'tabla_2_personas';
```

### 3. Analizar en Python
```python
# Contar cuántas veces se vendió cada extra
from collections import Counter

all_extras = Counter()
for extras_str in df['Extras (JSON)']:
    extras = json.loads(extras_str)
    for extra, cantidad in extras.items():
        all_extras[extra] += cantidad

print(all_extras.most_common(5))
# Output: [('tabla_2_personas', 15), ('cerveza_artesanal_negra', 22), ...]
```

## 🔍 Análisis de Registros Huérfanos

Los 9 registros huérfanos encontrados en enero indican:

### Posibles Causas:
1. **Horarios diferentes** (ej: 19:00:00 en Info vs 19:30:00 en Appointment)
2. **Reservas canceladas** después de crear Info Reserva
3. **Errores de captura** manual
4. **Pruebas** que quedaron en Info Reservas

### Ejemplo de Huérfana:
```
Fecha: 10/01/2026 11:00:00
Extras: tabla_2_personas, fanta, cerveza
Ingreso perdido: $38,400
```

**Acción:** Revisar estos registros manualmente para recuperar ingresos perdidos.

## 📊 Casos de Uso

### 1. Análisis de Extras
```python
import pandas as pd
import json

df = pd.read_csv('reservas_extras_20260101_20260131.csv')

# Ver reservas sin extras
sin_extras = df[df['Ingreso Extras'] == 0]
print(f"Reservas sin extras: {len(sin_extras)} ({len(sin_extras)/len(df)*100:.1f}%)")

# Ver top extras
extras_count = {}
for extras_str in df['Extras (JSON)']:
    extras = json.loads(extras_str)
    for extra, cant in extras.items():
        extras_count[extra] = extras_count.get(extra, 0) + cant

# Top 5
top_5 = sorted(extras_count.items(), key=lambda x: x[1], reverse=True)[:5]
for extra, count in top_5:
    print(f"{extra}: {count}")
```

### 2. Identificar Cruces Faltantes
```python
# Reservas sin cruce
sin_cruce = df[df['Tiene Cruce'] == 'No']
print(f"Reservas sin Info Reserva: {len(sin_cruce)}")

# Revisar huérfanas
huerfanas = pd.read_csv('reservas_extras_20260101_20260131_huerfanas.csv')
print(f"Info Reservas sin Appointment: {len(huerfanas)}")

# Ingresos perdidos en huérfanas
ingresos_perdidos = huerfanas['Ingreso Extras'].sum()
print(f"Ingresos potencialmente perdidos: ${ingresos_perdidos:,.0f}")
```

### 3. Validar Integridad
```python
# Verificar que JSON es válido
def validar_json(json_str):
    try:
        json.loads(json_str)
        return True
    except:
        return False

df['json_valido'] = df['Extras (JSON)'].apply(validar_json)
print(f"JSONs inválidos: {(~df['json_valido']).sum()}")
```

## 🔧 Cómo Funciona el Cruce

### Método Usado (Igual que `export_daily_analysis.py`)

```sql
-- 1. Preparar appointments con ROW_NUMBER
WITH appointments_data AS (
    SELECT 
        id,
        DATE(start_date) as fecha,
        TIME(start_date) as hora,
        payment_amount,
        ROW_NUMBER() OVER (
            PARTITION BY DATE(start_date), TIME(start_date)
            ORDER BY id
        ) as row_num
    FROM booknetic_appointments
),
-- 2. Preparar info reservas con ROW_NUMBER
reservations_with_extras AS (
    SELECT 
        id,
        DATE(fecha) as fecha,
        horario_salida as hora,
        extras_json,
        ROW_NUMBER() OVER (
            PARTITION BY DATE(fecha), horario_salida
            ORDER BY created_at
        ) as row_num
    FROM "Informacion Reservas"
)
-- 3. CRUZAR por fecha + hora + row_number
SELECT *
FROM appointments_data a
LEFT JOIN reservations_with_extras r
    ON a.fecha = r.fecha
    AND a.hora = r.hora
    AND a.row_num = r.row_num
```

### ¿Por Qué Funciona Mejor?

1. **Fuente correcta:** Usa `booknetic_appointments.payment` (no payments separado)
2. **ROW_NUMBER:** Maneja múltiples reservas en la misma hora
3. **LEFT JOIN:** No pierde appointments sin info
4. **Validación:** Identifica huérfanos

## ⚙️ Configuración

### Costos Fijos (en el script)
```python
COSTO_FIJO_POR_RESERVA = 18000  # $18,000
# Desglose:
# - Gas:    $15,000
# - Leña:   $1,000
# - Agua:   $1,000
# - Hielo:  $1,000
```

Para cambiar, edita el valor en `export_reservas_con_extras.py` línea ~220.

## 🐛 Solución de Problemas

### "No se encontraron reservas"
- Verifica las fechas (formato: YYYY-MM-DD)
- Verifica que hay appointments en ese rango

### "Muchas huérfanas"
Posibles causas:
1. Horarios no coinciden exactamente
2. Appointments fueron cancelados
3. Datos de prueba en "Informacion Reservas"

**Solución:** Revisar manualmente el CSV de huérfanas

### "JSON inválido"
Si el JSON tiene caracteres especiales:
- El script usa `ensure_ascii=False` para soportar tildes
- Excel puede no mostrarlo bien, usa VS Code o un editor JSON

## 📝 Próximos Pasos

1. **Revisar huérfanas** del CSV para recuperar ingresos
2. **Validar ingresos** con reportes contables
3. **Automatizar** este export mensualmente
4. **Crear dashboard** usando estos datos

## 🔗 Scripts Relacionados

| Script | Qué Hace |
|--------|----------|
| `export_reservas_con_extras.py` | ✅ Este script (con JSON) |
| `export_reservations_full.py` | Anterior (sin JSON, payment=0) |
| `export_daily_analysis.py` | Análisis diario (3 CSVs) |
| `analizar_reservas.py` | Genera reporte ejecutivo |

## Ver También

- [CRUCE_TABLAS.md](CRUCE_TABLAS.md) - Explicación técnica del cruce
- [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md) - Script anterior
- [EJEMPLO_CRUCE_TABLAS.md](EJEMPLO_CRUCE_TABLAS.md) - Ejemplo visual
