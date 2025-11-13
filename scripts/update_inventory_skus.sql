-- Script para actualizar SKUs en inventory con códigos cortos y descriptivos
-- Ejecutar UNA SOLA VEZ en tu base de datos

-- CERVEZAS
UPDATE inventory SET sku = 'CRV-AUCAL' WHERE LOWER(product_name) = LOWER('Cerveza Austral Calafate');
UPDATE inventory SET sku = 'CRV-AULAG' WHERE LOWER(product_name) = LOWER('Cerveza Austral Lager');
UPDATE inventory SET sku = 'CRV-KUVAL' WHERE LOWER(product_name) = LOWER('Cerveza Kunstman Valdivia');
UPDATE inventory SET sku = 'CRV-KUTOR' WHERE LOWER(product_name) = LOWER('Cerveza Kunstman Torobayo');
UPDATE inventory SET sku = 'CRV-ARTAMB' WHERE LOWER(product_name) = LOWER('Cerveza Artesanal Ambar');
UPDATE inventory SET sku = 'CRV-ARTNEG' WHERE LOWER(product_name) = LOWER('Cerveza Artesanal Negra');
UPDATE inventory SET sku = 'CRV-ROYAL' WHERE LOWER(product_name) = LOWER('Cerveza Royal');

-- CHAMPAÑA
UPDATE inventory SET sku = 'CHP-RICRUBY' WHERE LOWER(product_name) = LOWER('Champaña Riccadonna Ruby');
UPDATE inventory SET sku = 'CHP-RICMROS' WHERE LOWER(product_name) = LOWER('Champaña Riccadonna Moscato Rose');
UPDATE inventory SET sku = 'CHP-RICASTI' WHERE LOWER(product_name) = LOWER('Champaña Riccadonna Asti');
UPDATE inventory SET sku = 'CHP-RAMAZ' WHERE LOWER(product_name) = LOWER('Champaña para Ramazotti');

-- LICORES Y APERITIVOS
UPDATE inventory SET sku = 'LIC-RAMAZ' WHERE LOWER(product_name) = LOWER('Ramazotti');
UPDATE inventory SET sku = 'LIC-LEMON' WHERE LOWER(product_name) = LOWER('Lemon Stone');
UPDATE inventory SET sku = 'LIC-MARAC' WHERE LOWER(product_name) = LOWER('Maracuya Stone');

-- VINOS
UPDATE inventory SET sku = 'VIN-CARMEN' WHERE LOWER(product_name) = LOWER('Vino Carmenere');
UPDATE inventory SET sku = 'VIN-CABSAU' WHERE LOWER(product_name) = LOWER('Vino Cabernet Sauvignon');
UPDATE inventory SET sku = 'VIN-MERLOT' WHERE LOWER(product_name) = LOWER('Vino Merlot');

-- BEBIDAS Y JUGOS
UPDATE inventory SET sku = 'BEB-COCA' WHERE LOWER(product_name) = LOWER('Coca-cola');
UPDATE inventory SET sku = 'BEB-FANTA' WHERE LOWER(product_name) = LOWER('Fanta');
UPDATE inventory SET sku = 'JUG-MANNAR' WHERE LOWER(product_name) = LOWER('Jugo Mango Naranja');
UPDATE inventory SET sku = 'JUG-NARANJA' WHERE LOWER(product_name) = LOWER('Jugo Naranja');
UPDATE inventory SET sku = 'JUG-BERRIES' WHERE LOWER(product_name) = LOWER('Jugo Berries');

-- TABLAS
UPDATE inventory SET sku = 'TBL-2P' WHERE LOWER(product_name) = LOWER('Tabla 2 Personas');
UPDATE inventory SET sku = 'TBL-4P' WHERE LOWER(product_name) = LOWER('Tabla 4 Personas');

-- EXTRAS
UPDATE inventory SET sku = 'EXT-CHALAS' WHERE LOWER(product_name) = LOWER('Chalas');
UPDATE inventory SET sku = 'EXT-TOALLA' WHERE LOWER(product_name) = LOWER('Toalla');
UPDATE inventory SET sku = 'EXT-TPONCHO' WHERE LOWER(product_name) = LOWER('Toalla Poncho');
UPDATE inventory SET sku = 'EXT-ROMAN' WHERE LOWER(product_name) = LOWER('Modo Romantico');
UPDATE inventory SET sku = 'EXT-VID15' WHERE LOWER(product_name) = LOWER('Video 15 Segundos');
UPDATE inventory SET sku = 'EXT-VID60' WHERE LOWER(product_name) = LOWER('Video 60 Segundos');

-- Verificar resultados
SELECT id, product_name, sku, quantity, min_stock 
FROM inventory 
ORDER BY sku;

