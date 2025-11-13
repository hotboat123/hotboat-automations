-- Limpieza de duplicados en inventory
-- Revisa y respalda antes de ejecutar en producción

BEGIN;

-- 1) Duplicados por SKU (mismo sku en varias filas)
WITH ranked AS (
    SELECT
        id,
        sku,
        ROW_NUMBER() OVER (PARTITION BY sku ORDER BY id DESC) AS rn
    FROM inventory
    WHERE sku IS NOT NULL
)
DELETE FROM inventory i
USING ranked r
WHERE i.id = r.id
  AND r.rn > 1;

-- 2) Duplicados por nombre cuando SKU es NULL
WITH ranked_names AS (
    SELECT
        id,
        LOWER(product_name) AS lname,
        ROW_NUMBER() OVER (PARTITION BY LOWER(product_name) ORDER BY id DESC) AS rn
    FROM inventory
    WHERE sku IS NULL
)
DELETE FROM inventory i
USING ranked_names r
WHERE i.id = r.id
  AND r.rn > 1;

COMMIT;

-- Verificación rápida
-- SELECT sku, COUNT(*) FROM inventory WHERE sku IS NOT NULL GROUP BY sku HAVING COUNT(*) > 1;
-- SELECT LOWER(product_name) AS name, COUNT(*) FROM inventory WHERE sku IS NULL GROUP BY LOWER(product_name) HAVING COUNT(*) > 1;


