-- Migración 005: Crear tabla reservas_con_extras (tabla materializada)
-- Esta tabla almacena los datos ya cruzados entre appointments, payments e Informacion Reservas
-- Se actualiza automáticamente mediante un monitor

CREATE TABLE IF NOT EXISTS reservas_con_extras (
    -- IDs
    id SERIAL PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    reservation_id TEXT,
    
    -- Fecha y hora
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    
    -- Cliente
    nombre_cliente TEXT,
    email TEXT,
    telefono TEXT,
    
    -- Servicio
    servicio TEXT,
    num_personas INTEGER,
    
    -- Ingresos
    ingreso_reserva NUMERIC(10, 2) DEFAULT 0,
    ingreso_extras NUMERIC(10, 2) DEFAULT 0,
    ingreso_total NUMERIC(10, 2) DEFAULT 0,
    
    -- Costos operativos
    costo_operativo_fijo NUMERIC(10, 2) DEFAULT 18000,  -- Gas + Leña + Agua + Hielo
    costo_operativo_variable NUMERIC(10, 2) DEFAULT 0,
    costo_operativo_total NUMERIC(10, 2) DEFAULT 18000,
    
    -- Datos adicionales del cliente
    num_adultos INTEGER DEFAULT 0,
    num_ninos INTEGER DEFAULT 0,
    ciudad_origen TEXT,
    como_supieron TEXT,
    clima_del_dia TEXT,
    categoria_clientes TEXT,
    tipo_clientes TEXT,
    
    -- Estado
    status TEXT,
    tiene_cruce BOOLEAN DEFAULT FALSE,
    
    -- Extras en formato JSON
    extras_json JSONB,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices para búsquedas rápidas
    CONSTRAINT unique_appointment_date UNIQUE (appointment_id, fecha)
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_reservas_extras_fecha ON reservas_con_extras(fecha);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_appointment_id ON reservas_con_extras(appointment_id);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_reservation_id ON reservas_con_extras(reservation_id);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_fecha_hora ON reservas_con_extras(fecha, hora);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_tiene_cruce ON reservas_con_extras(tiene_cruce);
CREATE INDEX IF NOT EXISTS idx_reservas_extras_created_at ON reservas_con_extras(created_at);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_reservas_extras_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at
DROP TRIGGER IF EXISTS trigger_update_reservas_extras_updated_at ON reservas_con_extras;
CREATE TRIGGER trigger_update_reservas_extras_updated_at
    BEFORE UPDATE ON reservas_con_extras
    FOR EACH ROW
    EXECUTE FUNCTION update_reservas_extras_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE reservas_con_extras IS 'Tabla materializada con datos cruzados de appointments, payments e Informacion Reservas';
COMMENT ON COLUMN reservas_con_extras.appointment_id IS 'ID del appointment en booknetic_appointments';
COMMENT ON COLUMN reservas_con_extras.reservation_id IS 'ID de la información de reserva';
COMMENT ON COLUMN reservas_con_extras.ingreso_reserva IS 'Ingreso base de la reserva (payment de booknetic)';
COMMENT ON COLUMN reservas_con_extras.ingreso_extras IS 'Ingreso adicional por extras';
COMMENT ON COLUMN reservas_con_extras.ingreso_total IS 'Suma de ingreso_reserva + ingreso_extras';
COMMENT ON COLUMN reservas_con_extras.costo_operativo_fijo IS 'Costo fijo por reserva (Gas + Leña + Agua + Hielo = $18,000)';
COMMENT ON COLUMN reservas_con_extras.costo_operativo_variable IS 'Costos variables (extras)';
COMMENT ON COLUMN reservas_con_extras.tiene_cruce IS 'TRUE si cruzó con Informacion Reservas, FALSE si no';
COMMENT ON COLUMN reservas_con_extras.extras_json IS 'Extras en formato JSON: {"nombre_extra": cantidad, ...}';
