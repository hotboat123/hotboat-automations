-- Ejecutar esta migración en Railway para crear la tabla de sincronización con Google Sheets

-- Crear tabla intermedia para sincronización con Google Sheets
CREATE TABLE IF NOT EXISTS "Reservas_Con_Extras_Sheets" (
    id SERIAL PRIMARY KEY,
    raw JSONB NOT NULL,
    source TEXT DEFAULT 'reservas_con_extras',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índice único para evitar duplicados
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_reserva_sheets 
    ON "Reservas_Con_Extras_Sheets" ((raw->>'appointment_id'), (raw->>'fecha'));

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_reservas_sheets_fecha 
    ON "Reservas_Con_Extras_Sheets" ((raw->>'fecha'));

CREATE INDEX IF NOT EXISTS idx_reservas_sheets_appointment 
    ON "Reservas_Con_Extras_Sheets" ((raw->>'appointment_id'));

CREATE INDEX IF NOT EXISTS idx_reservas_sheets_updated 
    ON "Reservas_Con_Extras_Sheets" (updated_at);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_reservas_sheets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at
DROP TRIGGER IF EXISTS trigger_update_reservas_sheets_updated_at 
    ON "Reservas_Con_Extras_Sheets";
    
CREATE TRIGGER trigger_update_reservas_sheets_updated_at
    BEFORE UPDATE ON "Reservas_Con_Extras_Sheets"
    FOR EACH ROW
    EXECUTE FUNCTION update_reservas_sheets_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE "Reservas_Con_Extras_Sheets" IS 
    'Tabla intermedia para sincronizar reservas_con_extras con Google Sheets via hotboat-etl';
COMMENT ON COLUMN "Reservas_Con_Extras_Sheets".raw IS 
    'Datos de la reserva en formato JSON compatible con Google Sheets';
COMMENT ON COLUMN "Reservas_Con_Extras_Sheets".source IS 
    'Origen de los datos (siempre reservas_con_extras)';
