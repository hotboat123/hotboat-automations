# Script de Cálculo de Ingresos Diarios

## Descripción

Este script (`calculate_daily_revenue.py`) calcula los ingresos diarios de ventas cruzando las tablas:
- **booknetic_payments**: Contiene los pagos de las reservas
- **Informacion Reservas**: Contiene la información de extras (bebidas, tablas, etc.)
- **Precios Extras**: Contiene los precios de venta de cada extra

### Novedades de esta versión:
- ✅ Lee precios desde la base de datos (tabla "Precios Extras")
- ✅ Sistema de categorías y aliases para mapear variantes de nombres
- ✅ Detecta y alerta sobre extras sin precio asignado
- ✅ Elimina duplicados automáticamente

## Uso

### Calcular ingresos para hoy
```bash
python scripts/calculate_daily_revenue.py
```

### Calcular ingresos para una fecha específica
```bash
python scripts/calculate_daily_revenue.py 2026-01-15
```

### Calcular ingresos para un rango de fechas
```bash
python scripts/calculate_daily_revenue.py 2026-01-01 2026-01-31
```

### Calcular sin exportar a CSV
```bash
python scripts/calculate_daily_revenue.py 2026-01-15 --no-csv
```

## Estructura de datos

### Ingresos totales
El script calcula:
- **Ingresos por reservas**: Suma de `total_amount` de booknetic_payments
- **Ingresos por extras**: Suma del valor de todos los extras consumidos
- **TOTAL**: Ingresos por reservas + Ingresos por extras

### Extras detectados
El script detecta automáticamente los siguientes tipos de extras:
- **Cervezas**: Austral, Kunstmann, Royal, Artesanales
- **Champañas**: Riccadonna (Ruby, Moscato Rose, Asti), etc.
- **Licores**: Ramazotti, Lemon Stone, Maracuyá Stone
- **Vinos**: Carmenere, Cabernet Sauvignon, Merlot
- **Bebidas**: Coca-Cola, Fanta, Sprite, Jugos
- **Tablas**: Tabla 2 personas, Tabla 4 personas
- **Otros extras**: Chalas, Toallas, Modo Romántico, Videos, etc.

## Archivos generados

El script genera archivos CSV con el formato:
- `ingresos_YYYY-MM-DD.csv`: Un archivo por fecha

Cada archivo CSV contiene:
- Detalles de cada reserva (Payment ID, Cliente, Fecha, Estado, Totales)
- Listado de extras por reserva
- Resumen total del día

## Precios de extras

### Fuente de precios
Los precios se cargan automáticamente desde la tabla **"Precios Extras"** de la base de datos.

### Sistema de categorías y aliases

El script usa un sistema de categorías para mapear variantes de nombres a un precio común.

**Ejemplo**: Todas estas variantes mapean a "Champaña Riccadona" ($22,000):
- `champaña_riccadonna_ruby`
- `champaña_riccadonna_moscato_rose`
- `champaña_riccadonna_asti`
- `riccadonna_ruby`
- `riccadonna` (genérico)

### Configurar nuevas categorías o aliases

Para agregar nuevas categorías, edita la función `get_category_aliases()` en el script:

```python
def get_category_aliases() -> Dict[str, List[str]]:
    return {
        'champana_riccadona': [  # Categoría en "Precios Extras"
            'champana_riccadonna_ruby',  # Variantes
            'champana_riccadonna_moscato_rose',
            'riccadonna_ruby',
            # ... más aliases
        ],
        'cerveza_artesanal': [
            'cerveza_artesanal_ambar',
            'cerveza_artesanal_negra',
            # ... más aliases
        ]
    }
```

### Alertas de extras sin precio

Si el script encuentra extras sin precio asignado, mostrará una alerta al final:

```
[ALERTA] EXTRAS SIN PRECIO ASIGNADO
Se encontraron 2 extras sin precio:
   - tabla_8_personas
   - cerveza_nueva_marca

Por favor, actualice estos extras en:
   1. La tabla 'Precios Extras' de la base de datos, O
   2. La función get_category_aliases() en el script
```

## Problemas conocidos y soluciones

### ✅ Duplicados en resultados (RESUELTO)
**Problema**: Algunas reservas aparecían múltiples veces porque había varios registros en "Informacion Reservas" para la misma fecha/hora.

**Solución**: El script usa `DISTINCT ON (payment_id)` para eliminar duplicados automáticamente.

### ✅ Extras con precio $0 (RESUELTO)
**Problema**: Variantes de nombres (con tildes o espacios) no coincidían con el mapeo de precios.

**Solución**: 
1. Se agregó función `normalize_text()` para manejar tildes y espacios
2. Se implementó sistema de categorías y aliases
3. El script ahora alerta cuando encuentra extras sin precio

### ⚠️ Cruce de tablas por fecha
**Problema**: El cruce se hace por fecha + hora, pero los formatos pueden no coincidir exactamente.

**Estado**: Funciona en la mayoría de casos. Si una reserva no muestra extras, verificar que la hora coincida exactamente entre ambas tablas.

**Solución**: Si hay problemas, revisar los campos `horario_salida` en "Informacion Reservas" y `appointment_date` en "booknetic_payments".

## Ejemplos de resultados

### Ejemplo 1: 11 de enero de 2026
```
Total de reservas: 3
Ingresos por reservas: $557,870
Ingresos por extras: $104,000
TOTAL: $661,870

Detalles:
- Reserva 458: $197,940 + $52,000 extras = $249,940
  Extras: cerveza_artesanal_negra x5 ($30,000), champaña_riccadonna_ruby x1 ($22,000)
  
- Reserva 459: $194,950 + $52,000 extras = $246,950
  Extras: cerveza_artesanal_negra x5 ($30,000), champaña_riccadonna_ruby x1 ($22,000)
  
- Reserva 607: $164,980 + $0 extras = $164,980
```

### Ejemplo 2: 16 de enero de 2026
```
Total de reservas: 2
Ingresos por reservas: $416,944
Ingresos por extras: $0 (sin información de extras para esta fecha)
TOTAL: $416,944
```

### Ejemplo con alertas
Si hay extras sin precio:
```
[ALERTA] EXTRAS SIN PRECIO ASIGNADO
Se encontraron 1 extras sin precio:
   - tabla_8_personas

Por favor, actualice estos extras en:
   1. La tabla 'Precios Extras' de la base de datos, O
   2. La función get_category_aliases() en el script
```

## Notas técnicas

- El script usa `asyncio` para consultas asíncronas a la base de datos
- Los datos se extraen del campo `raw` (JSONB) de ambas tablas
- Las fechas se normalizan de formato DD/MM/YYYY a timestamp para el cruce
- Los montos se limpian de formato ($XX.XXX) y se convierten a numéricos

## Soporte

Para problemas o mejoras, contactar al equipo de desarrollo.
