-- Este script evita violar la restricción UNIQUE de sku cuando existen
-- productos duplicados en inventory. Para cada nombre de producto, solo
-- actualiza una fila (la más reciente que ya tenga el sku correcto o, en su
-- defecto, la de id mayor).

WITH product_skus (product_name, target_sku) AS (
    VALUES
        -- CERVEZAS
        ('Cerveza Austral Calafate', 'CRV-AUCAL'),
        ('Cerveza Austral Lager', 'CRV-AULAG'),
        ('Cerveza Kunstman Valdivia', 'CRV-KUVAL'),
        ('Cerveza Kunstman Torobayo', 'CRV-KUTOR'),
        ('Cerveza Artesanal Ambar', 'CRV-ARTAMB'),
        ('Cerveza Artesanal Negra', 'CRV-ARTNEG'),
        ('Cerveza Royal', 'CRV-ROYAL'),

        -- CHAMPAÑA
        ('Champaña Riccadonna Ruby', 'CHP-RICRUBY'),
        ('Champaña Riccadonna Moscato Rose', 'CHP-RICMROS'),
        ('Champaña Riccadonna Asti', 'CHP-RICASTI'),
        ('Champaña para Ramazotti', 'CHP-RAMAZ'),

        -- LICORES Y APERITIVOS
        ('Ramazotti', 'LIC-RAMAZ'),
        ('Lemon Stone', 'LIC-LEMON'),
        ('Maracuya Stone', 'LIC-MARAC'),

        -- VINOS
        ('Vino Carmenere', 'VIN-CARMEN'),
        ('Vino Cabernet Sauvignon', 'VIN-CABSAU'),
        ('Vino Merlot', 'VIN-MERLOT'),

        -- BEBIDAS Y JUGOS
        ('Coca-cola', 'BEB-COCA'),
        ('Fanta', 'BEB-FANTA'),
        ('Jugo Mango Naranja', 'JUG-MANNAR'),
        ('Jugo Naranja', 'JUG-NARANJA'),
        ('Jugo Berries', 'JUG-BERRIES'),

        -- TABLAS
        ('Tabla 2 Personas', 'TBL-2P'),
        ('Tabla 4 Personas', 'TBL-4P'),

        -- EXTRAS
        ('Chalas', 'EXT-CHALAS'),
        ('Toalla', 'EXT-TOALLA'),
        ('Toalla Poncho', 'EXT-TPONCHO'),
        ('Modo Romantico', 'EXT-ROMAN'),
        ('Video 15 Segundos', 'EXT-VID15'),
        ('Video 60 Segundos', 'EXT-VID60')
),
ranked_inventory AS (
    SELECT
        i.id,
        ps.target_sku,
        ROW_NUMBER() OVER (
            PARTITION BY LOWER(i.product_name)
            ORDER BY
                CASE WHEN i.sku = ps.target_sku THEN 0 ELSE 1 END,
                i.last_updated DESC NULLS LAST,
                i.created_at DESC NULLS LAST,
                i.id DESC
        ) AS rn
    FROM inventory i
    JOIN product_skus ps
        ON LOWER(i.product_name) = LOWER(ps.product_name)
),
updated_inventory AS (
    UPDATE inventory i
    SET sku = r.target_sku
    FROM ranked_inventory r
    WHERE i.id = r.id
      AND r.rn = 1
    RETURNING i.id, i.product_name, i.sku, i.quantity, i.min_stock
)
SELECT id, product_name, sku, quantity, min_stock
FROM inventory
WHERE LOWER(product_name) IN (
    SELECT LOWER(product_name) FROM product_skus
)
ORDER BY sku;

-- Opcional: revisar si quedaron duplicados sin actualizar
-- SELECT product_name, sku FROM inventory WHERE LOWER(product_name) IN (
--     SELECT LOWER(product_name) FROM product_skus
-- ) ORDER BY product_name, sku;

