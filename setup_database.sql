-- Script para crear la tabla de inventario (si no existe)
-- Ejecuta esto en tu base de datos PostgreSQL

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

-- Datos de ejemplo (opcional)
INSERT INTO inventory (product_name, sku, category, quantity, unit, min_stock, notes)
VALUES 
    ('Chalecos Salvavidas', 'SAFE-001', 'Seguridad', 15, 'unidades', 10, 'Chalecos de seguridad para pasajeros'),
    ('Combustible Gasolina', 'FUEL-001', 'Combustible', 50, 'litros', 100, 'Gasolina para embarcaciones'),
    ('Aceite Motor 2T', 'OIL-001', 'Mantenimiento', 3, 'litros', 5, 'Aceite para motores de 2 tiempos'),
    ('Botellas de Agua', 'BEV-001', 'Bebidas', 8, 'unidades', 20, 'Agua embotellada para clientes'),
    ('Botiquín Primeros Auxilios', 'SAFE-002', 'Seguridad', 2, 'unidades', 2, 'Botiquín de emergencia'),
    ('Aros Salvavidas', 'SAFE-003', 'Seguridad', 4, 'unidades', 4, 'Aros de rescate'),
    ('Toallas', 'ACC-001', 'Accesorios', 12, 'unidades', 15, 'Toallas para clientes')
ON CONFLICT (sku) DO NOTHING;

-- Verificar que la tabla appointments existe (para el monitor)
-- Si no existe, aquí hay un ejemplo básico
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50),
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration_hours DECIMAL(3,1) DEFAULT 2.0,
    boat_type VARCHAR(100),
    num_people INTEGER,
    total_price DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Índices para appointments
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(phone_number);

COMMENT ON TABLE inventory IS 'Tabla de inventario para el sistema de automatizaciones';
COMMENT ON TABLE appointments IS 'Tabla de citas/reservas para el sistema de automatizaciones';

