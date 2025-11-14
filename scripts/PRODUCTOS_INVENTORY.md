# 📦 Productos en Inventory

## Listado Completo de Productos con SKUs

Este documento lista todos los 31 productos configurados en el sistema con sus SKUs y aliases soportados.

---

## 🍺 CERVEZAS (7 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 1 | Cerveza Austral Calafate | `CRV-AUCAL` | `cerveza_austral_calafate`, `austral_calafate` | 10 |
| 2 | Cerveza Austral Lager | `CRV-AULAG` | `cerveza_austral_lager`, `austral_lager` | 10 |
| 3 | Cerveza Kunstman Valdivia | `CRV-KUVAL` | `cerveza_kunstman_valdivia`, `kunstman_valdivia` | 10 |
| 4 | Cerveza Kunstman Torobayo | `CRV-KUTOR` | `cerveza_kunstman_torobayo`, `kunstman_torobayo` | 10 |
| 5 | Cerveza Artesanal Ambar | `CRV-ARTAMB` | `cerveza_artesanal_ambar`, `artesanal_ambar` | 10 |
| 6 | Cerveza Artesanal Negra | `CRV-ARTNEG` | `cerveza_artesanal_negra`, `artesanal_negra` | 10 |
| 7 | Cerveza Royal | `CRV-ROYAL` | `cerveza_royal`, `royal` | 10 |

---

## 🍾 CHAMPAÑA (4 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 8 | Champaña Riccadonna Ruby | `CHP-RICRUBY` | `champaña_riccadonna_ruby`, `riccadonna_ruby` | 5 |
| 9 | Champaña Riccadonna Moscato Rose | `CHP-RICMROS` | `champaña_riccadonna_moscato_rose`, `riccadonna_moscato_rose` | 5 |
| 10 | Champaña Riccadonna Asti | `CHP-RICASTI` | `champaña_riccadonna_asti`, `riccadonna_asti` | 5 |
| 11 | Champaña para Ramazotti | `CHP-RAMAZ` | `champaña_para_ramazotti`, `para_ramazotti` | 5 |

---

## 🥃 LICORES (3 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 12 | Ramazotti | `LIC-RAMAZ` | `ramazotti` | 5 |
| 13 | Lemon Stone | `LIC-LEMON` | `lemon_stone`, `lemon_stone_normal`, `lemon stone` | 5 |
| 14 | Maracuya Stone | `LIC-MARAC` | `maracuya_stone`, `maracuya_stone_`, `maracuya stone` | 5 |

---

## 🍷 VINOS (3 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 15 | Vino Carmenere | `VIN-CARMEN` | `vino_carmenere`, `carmenere` | 8 |
| 16 | Vino Cabernet Sauvignon | `VIN-CABSAU` | `vino_cabernet_sauvignon`, `cabernet_sauvignon`, `cabernet sauvignon` | 8 |
| 17 | Vino Merlot | `VIN-MERLOT` | `vino_merlot`, `merlot` | 8 |

---

## 🥤 BEBIDAS (2 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 18 | Coca-cola | `BEB-COCA` | `coca-cola`, `coca_cola`, `coca cola` | 20 |
| 19 | Fanta | `BEB-FANTA` | `fanta` | 15 |

---

## 🧃 JUGOS (3 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 20 | Jugo Mango Naranja | `JUG-MANNAR` | `jugo_mango_naranja`, `mango_naranja` | 10 |
| 21 | Jugo Naranja | `JUG-NARANJA` | `jugo_naranja`, `naranja` | 10 |
| 22 | Jugo Berries | `JUG-BERRIES` | `jugo_berries`, `berries` | 10 |

---

## 🍽️ TABLAS (2 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 23 | Tabla 2 Personas | `TBL-2P` | `tabla_2_personas`, `tabla_2`, `tabla 2 personas` | 3 |
| 24 | Tabla 4 Personas | `TBL-4P` | `tabla_4_personas`, `tabla_4`, `tabla 4 personas` | 3 |

---

## 🏖️ EXTRAS (7 productos)

| # | Producto | SKU | Aliases soportados | Min Stock |
|---|----------|-----|-------------------|-----------|
| 25 | Chalas | `EXT-CHALAS` | `chalas` | 15 |
| 26 | Toalla | `EXT-TOALLA` | `toalla` | 20 |
| 27 | Toalla Poncho | `EXT-TPONCHO` | `toalla_poncho`, `toalla poncho` | 10 |
| 28 | Modo Romantico | `EXT-ROMAN` | `modo_romantico`, `modo romantico`, `romantico` | 5 |
| 29 | Video 15 Segundos | `EXT-VID15` | `video_15_segundos`, `video_15`, `video 15 segundos` | 100 |
| 30 | Video 60 Segundos | `EXT-VID60` | `video_60_segundos`, `video_60`, `video 60 segundos` | 100 |

---

## 📝 Notas Importantes

### Aliases
Los aliases son los nombres que aparecen en el campo `raw` de "Información Reservas" entre corchetes.

**Ejemplo de formato**:
```json
{
  "extras_tipo_1_[cerveza_royal]": "3",
  "bebidas_y_jugos_tipo_1_[coca_cola]": "2",
  "tablas_[tabla_2_personas]": "1"
}
```

El sistema automáticamente:
1. Extrae el alias entre corchetes: `[cerveza_royal]` → `cerveza_royal`
2. Lo convierte a minúsculas
3. Lo busca en la tabla de mapeo
4. Obtiene el SKU correspondiente: `CRV-ROYAL`
5. Busca el producto en inventory por SKU

### Case Insensitive
Los aliases NO son case-sensitive:
- `cerveza_royal` = `Cerveza_Royal` = `CERVEZA_ROYAL` ✅

### Espacios vs Guiones Bajos
El sistema soporta ambos:
- `coca_cola` = `coca-cola` = `coca cola` ✅

### Añadir Nuevos Aliases
Si necesitas añadir un nuevo alias para un producto existente, edita `setup_database.sql` líneas 244-318:

```sql
WHEN 'nuevo_alias' THEN 'SKU-EXISTENTE'
```

---

## 🔍 Consultas Útiles

### Ver todos los productos
```sql
SELECT id, product_name, sku, category, quantity, min_stock 
FROM inventory 
ORDER BY category, sku;
```

### Ver productos de una categoría
```sql
SELECT product_name, sku, quantity, min_stock 
FROM inventory 
WHERE category = 'Cervezas'
ORDER BY product_name;
```

### Buscar un producto por nombre
```sql
SELECT * FROM inventory 
WHERE LOWER(product_name) LIKE '%royal%';
```

### Buscar un producto por SKU
```sql
SELECT * FROM inventory 
WHERE sku = 'CRV-ROYAL';
```

### Ver productos con stock bajo
```sql
SELECT product_name, sku, quantity, min_stock 
FROM inventory 
WHERE quantity <= min_stock 
ORDER BY quantity ASC;
```

---

## 📊 Estadísticas del Catálogo

| Categoría | Cantidad de Productos | Stock Mínimo Total |
|-----------|----------------------|-------------------|
| Cervezas | 7 | 70 unidades |
| Champaña | 4 | 20 unidades |
| Licores | 3 | 15 unidades |
| Vinos | 3 | 24 unidades |
| Bebidas | 2 | 35 unidades |
| Jugos | 3 | 30 unidades |
| Tablas | 2 | 6 unidades |
| Extras | 7 | 260 unidades |
| **TOTAL** | **31** | **460 unidades** |

---

## 🔄 Actualizar este Documento

Cuando añadas nuevos productos, actualiza este documento:

1. Añadir la fila en la tabla correspondiente
2. Actualizar el SKU en la columna SKU
3. Listar todos los aliases soportados
4. Actualizar la tabla de estadísticas al final
5. Actualizar el total de productos

---

**Última actualización**: 2025-11-14  
**Productos totales**: 31  
**Versión**: 1.0

