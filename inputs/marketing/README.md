# Carpeta de Inputs - Marketing

Esta carpeta contiene el archivo CSV de costos de marketing que se importa al sistema.

## 📁 Archivo esperado:

Coloca aquí tu archivo CSV exportado desde Meta Business Suite con el nombre:

```
marketing_costs.csv
```

## 🔄 Para actualizar los datos:

### Opción 1: Script simple (recomendado)
```bash
python scripts/update_marketing.py
```

Este script:
- ✅ Busca automáticamente el archivo `inputs/marketing/marketing_costs.csv`
- ✅ Reemplaza los datos existentes
- ✅ Muestra un resumen de lo importado

### Opción 2: Manual
```bash
python scripts/import_marketing_costs.py "inputs/marketing/marketing_costs.csv" --replace
```

## 📝 Proceso recomendado:

1. Exporta el CSV actualizado desde Meta Business Suite
2. Guárdalo como `marketing_costs.csv` en esta carpeta (reemplazando el anterior)
3. Ejecuta: `python scripts/update_marketing.py`
4. ¡Listo! Tus reportes ya tendrán los datos actualizados

## ⚠️ Importante:

- El archivo **debe llamarse exactamente** `marketing_costs.csv`
- El formato debe ser el mismo que exporta Meta Business Suite
- Siempre usa `--replace` para evitar duplicados
