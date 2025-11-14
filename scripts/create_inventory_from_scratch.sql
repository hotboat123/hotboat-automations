-- Script para crear la tabla inventory desde cero con productos predefinidos
-- Ejecutar en tu base de datos PostgreSQL

-- Eliminar la tabla si existe (opcional, usar con cuidado)
-- DROP TABLE IF EXISTS inventory CASCADE;

-- Crear la tabla inventory
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE,
    category VARCHAR(100),
    quantity INTEGER NOT NULL DEFAULT 0,
    unit VARCHAR(50) DEFAULT 'unidades',
    min_stock INTEGER DEFAULT 5,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Índices para mejor performance
CREATE INDEX IF NOT EXISTS idx_inventory_quantity ON inventory(quantity);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category);
CREATE INDEX IF NOT EXISTS idx_inventory_last_updated ON inventory(last_updated);

-- Evitar duplicados por nombre cuando SKU es nulo
CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_name_when_no_sku
ON inventory (LOWER(product_name))
WHERE sku IS NULL;

-- Insertar todos los productos con sus SKUs
INSERT INTO inventory (product_name, sku, category, quantity, min_stock) VALUES
    -- CERVEZAS
    ('Cerveza Austral Calafate', 'CRV-AUCAL', 'Cervezas', 0, 10),
    ('Cerveza Austral Lager', 'CRV-AULAG', 'Cervezas', 0, 10),
    ('Cerveza Kunstman Valdivia', 'CRV-KUVAL', 'Cervezas', 0, 10),
    ('Cerveza Kunstman Torobayo', 'CRV-KUTOR', 'Cervezas', 0, 10),
    ('Cerveza Artesanal Ambar', 'CRV-ARTAMB', 'Cervezas', 0, 10),
    ('Cerveza Artesanal Negra', 'CRV-ARTNEG', 'Cervezas', 0, 10),
    ('Cerveza Royal', 'CRV-ROYAL', 'Cervezas', 0, 10),
    
    -- CHAMPAÑA
    ('Champaña Riccadonna Ruby', 'CHP-RICRUBY', 'Champaña', 0, 5),
    ('Champaña Riccadonna Moscato Rose', 'CHP-RICMROS', 'Champaña', 0, 5),
    ('Champaña Riccadonna Asti', 'CHP-RICASTI', 'Champaña', 0, 5),
    ('Champaña para Ramazotti', 'CHP-RAMAZ', 'Champaña', 0, 5),
    
    -- LICORES Y APERITIVOS
    ('Ramazotti', 'LIC-RAMAZ', 'Licores', 0, 5),
    ('Lemon Stone', 'LIC-LEMON', 'Licores', 0, 5),
    ('Maracuya Stone', 'LIC-MARAC', 'Licores', 0, 5),
    
    -- VINOS
    ('Vino Carmenere', 'VIN-CARMEN', 'Vinos', 0, 8),
    ('Vino Cabernet Sauvignon', 'VIN-CABSAU', 'Vinos', 0, 8),
    ('Vino Merlot', 'VIN-MERLOT', 'Vinos', 0, 8),
    
    -- BEBIDAS Y JUGOS
    ('Coca-cola', 'BEB-COCA', 'Bebidas', 0, 20),
    ('Fanta', 'BEB-FANTA', 'Bebidas', 0, 15),
    ('Jugo Mango Naranja', 'JUG-MANNAR', 'Jugos', 0, 10),
    ('Jugo Naranja', 'JUG-NARANJA', 'Jugos', 0, 10),
    ('Jugo Berries', 'JUG-BERRIES', 'Jugos', 0, 10),
    
    -- TABLAS
    ('Tabla 2 Personas', 'TBL-2P', 'Tablas', 0, 3),
    ('Tabla 4 Personas', 'TBL-4P', 'Tablas', 0, 3),
    
    -- EXTRAS
    ('Chalas', 'EXT-CHALAS', 'Extras', 0, 15),
    ('Toalla', 'EXT-TOALLA', 'Extras', 0, 20),
    ('Toalla Poncho', 'EXT-TPONCHO', 'Extras', 0, 10),
    ('Modo Romantico', 'EXT-ROMAN', 'Extras', 0, 5),
    ('Video 15 Segundos', 'EXT-VID15', 'Extras', 0, 100),
    ('Video 60 Segundos', 'EXT-VID60', 'Extras', 0, 100)
ON CONFLICT (sku) DO NOTHING;

-- Trigger para actualizar last_updated automáticamente
CREATE OR REPLACE FUNCTION update_inventory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_inventory_timestamp ON inventory;
CREATE TRIGGER trigger_update_inventory_timestamp
    BEFORE UPDATE ON inventory
    FOR EACH ROW
    EXECUTE FUNCTION update_inventory_timestamp();

-- Verificar resultados
SELECT id, product_name, sku, category, quantity, min_stock 
FROM inventory 
ORDER BY category, sku;

-- Resumen por categoría
SELECT category, COUNT(*) as total_productos
FROM inventory
GROUP BY category
ORDER BY category;

