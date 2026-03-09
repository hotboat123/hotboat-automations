-- Migración para cambiar Reservas_Con_Extras_Sheets a formato de columnas
-- En vez de un JSON gigante, tendrá columnas individuales como reservas_con_extras

-- 1. Borrar la tabla actual
DROP TABLE IF EXISTS "Reservas_Con_Extras_Sheets" CASCADE;

-- 2. Crear tabla con estructura igual a reservas_con_extras
CREATE TABLE IF NOT EXISTS "Reservas_Con_Extras_Sheets" (
    id SERIAL PRIMARY KEY,
    
    -- IDs
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
    num_personas TEXT,
    
    -- Ingresos
    ingreso_reserva NUMERIC(10, 2) DEFAULT 0,
    ingreso_extras NUMERIC(10, 2) DEFAULT 0,
    ingreso_total NUMERIC(10, 2) DEFAULT 0,
    
    -- Costos
    costo_operativo_fijo NUMERIC(10, 2) DEFAULT 0,
    costo_operativo_variable NUMERIC(10, 2) DEFAULT 0,
    costo_operativo_total NUMERIC(10, 2) DEFAULT 0,
    
    -- Personas
    num_adultos INTEGER DEFAULT 0,
    num_ninos INTEGER DEFAULT 0,
    
    -- Metadata
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
    
    -- Metadata de tabla
    source TEXT DEFAULT 'reservas_con_extras',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraint único para evitar duplicados
    UNIQUE(appointment_id, fecha)
);

-- 3. Crear índices para mejorar performance
CREATE INDEX idx_sheets_fecha ON "Reservas_Con_Extras_Sheets"(fecha DESC);
CREATE INDEX idx_sheets_appointment_id ON "Reservas_Con_Extras_Sheets"(appointment_id);
CREATE INDEX idx_sheets_updated_at ON "Reservas_Con_Extras_Sheets"(updated_at DESC);

-- 4. Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_reservas_sheets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Trigger para actualizar updated_at
DROP TRIGGER IF EXISTS trigger_update_reservas_sheets_updated_at ON "Reservas_Con_Extras_Sheets";
CREATE TRIGGER trigger_update_reservas_sheets_updated_at
    BEFORE UPDATE ON "Reservas_Con_Extras_Sheets"
    FOR EACH ROW
    EXECUTE FUNCTION update_reservas_sheets_updated_at();

-- Comentarios
COMMENT ON TABLE "Reservas_Con_Extras_Sheets" IS 'Tabla intermedia con formato de columnas para sincronización con Google Sheets vía hotboat-etl';
COMMENT ON COLUMN "Reservas_Con_Extras_Sheets".source IS 'Origen de los datos (siempre reservas_con_extras)';
