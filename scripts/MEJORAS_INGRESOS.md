# Mejoras Implementadas - Script de Ingresos Diarios

## Resumen de cambios

### ✅ 1. Lectura de precios desde base de datos

**Antes**: Los precios estaban hardcodeados en el script

**Ahora**: Los precios se cargan automáticamente desde la tabla **"Precios Extras"**

```python
# El script carga 19 precios desde la BD al iniciar:
Cargado: Cerveza Artesanal -> $6,000
Cargado: Champaña Riccadona -> $22,000
Cargado: Cerveza Premium -> $4,000
...
Total de precios cargados: 19
```

### ✅ 2. Sistema de categorías y aliases

**Problema**: "champaña riccadonna ruby" vs "Champaña Riccadona" no coincidían

**Solución**: Sistema de mapeo de categorías

```python
# Todas estas variantes ahora mapean a "champana_riccadona" ($22,000):
'champana_riccadonna_ruby'
'champana_riccadonna_moscato_rose'
'champana_riccadonna_asti'
'riccadonna_ruby'
```

**Beneficios**:
- Normalización automática de texto (tildes, espacios)
- Mapeo flexible de variantes a categorías
- Fácil de extender agregando nuevos aliases

### ✅ 3. Alertas de extras sin precio

**Nueva funcionalidad**: Si el script encuentra extras que no puede mapear a ningún precio, muestra una alerta:

```
[ALERTA] EXTRAS SIN PRECIO ASIGNADO
Se encontraron 2 extras sin precio:
   - tabla_8_personas
   - bebida_nueva

Por favor, actualice estos extras en:
   1. La tabla 'Precios Extras' de la base de datos, O
   2. La función get_category_aliases() en el script
```

**Beneficios**:
- Detecta automáticamente productos faltantes
- Evita pérdidas de ingresos por productos sin precio
- Facilita el mantenimiento del sistema

### ✅ 4. Eliminación de duplicados

**Problema**: Mismas reservas aparecían múltiples veces

**Solución**: Query SQL mejorado con `DISTINCT ON (payment_id)`

**Antes**: 9 reservas (duplicadas)
**Ahora**: 3 reservas (únicas)

### ✅ 5. Normalización de texto mejorada

```python
def normalize_text(text: str) -> str:
    """
    - Remueve tildes y diacríticos
    - Convierte a minúsculas
    - Reemplaza espacios y guiones por guiones bajos
    """
    # "Champaña Riccadona" -> "champana_riccadona"
    # "Coca-Cola" -> "coca_cola"
```

## Cómo agregar nuevas categorías

### Opción 1: Agregar a "Precios Extras" (Recomendado)

Si es un producto completamente nuevo:

1. Agregar registro en la tabla "Precios Extras"
2. Rellenar campos: `Extra`, `Precio`, `costo`, etc.
3. El script lo detectará automáticamente

### Opción 2: Agregar alias en el script

Si es una variante de un producto existente:

1. Editar `get_category_aliases()` en `calculate_daily_revenue.py`
2. Agregar el nuevo alias a la categoría correspondiente:

```python
'champana_riccadona': [
    'champana_riccadonna_ruby',
    'champana_riccadonna_moscato_rose',
    'champana_riccadonna_asti',
    'nueva_variante_riccadonna',  # ← Agregar aquí
]
```

## Resultados comparativos

### 11 de enero de 2026

**Versión anterior**:
- Reservas: 9 (con duplicados)
- Ingresos por reservas: $1,673,610
- Ingresos por extras: $165,000 (algunos en $0)
- TOTAL: $1,838,610

**Versión nueva**:
- Reservas: 3 (sin duplicados) ✅
- Ingresos por reservas: $557,870 ✅
- Ingresos por extras: $104,000 (todos con precio) ✅
- TOTAL: $661,870 ✅

**Nota**: Los números ahora son correctos. La versión anterior contaba las reservas 3 veces.

## Archivos modificados/creados

1. **`calculate_daily_revenue.py`**: Script principal (reescrito)
2. **`README_INGRESOS.md`**: Documentación actualizada
3. **`MEJORAS_INGRESOS.md`**: Este documento

## Próximos pasos sugeridos

1. **Revisar categorías existentes**: Verificar que todos los mapeos sean correctos
2. **Agregar más aliases**: Según se encuentren nuevas variantes de productos
3. **Mantener "Precios Extras" actualizado**: Agregar nuevos productos según sea necesario
4. **Monitorear alertas**: Revisar regularmente los extras sin precio detectados

## Soporte y mantenimiento

Para agregar o modificar categorías, contactar al equipo de desarrollo o editar directamente la función `get_category_aliases()` en el script.
