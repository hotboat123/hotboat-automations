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

-- Evitar duplicados por nombre cuando SKU es nulo
CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_name_when_no_sku
ON inventory (LOWER(product_name))
WHERE sku IS NULL;

-- Sincronizar datos desde la tabla "Stock" (hoja de cálculo)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'Stock'
    ) THEN
        -- Eliminar datos de ejemplo iniciales, si existen
        DELETE FROM inventory
        WHERE sku IN ('SAFE-001', 'FUEL-001', 'OIL-001', 'BEV-001', 'SAFE-002', 'SAFE-003', 'ACC-001');

        INSERT INTO inventory (
            product_name,
            sku,
            category,
            quantity,
            unit,
            min_stock,
            last_updated,
            created_at,
            notes
        )
        SELECT
            NULLIF(TRIM(raw->>'Producto'), '') AS product_name,
            raw->>'id' AS sku,
            NULLIF(TRIM(raw->>'Categoría'), '') AS category,
            COALESCE(
                ROUND(
                    COALESCE(
                        NULLIF(
                            REPLACE(
                                REGEXP_REPLACE(TRIM(raw->>'Stock'), '[^0-9,.-]', '', 'g'),
                                ',',
                                '.'
                            ),
                            ''
                        )::NUMERIC,
                        0
                    )
                )::INTEGER,
                0
            ) AS quantity,
            'unidades' AS unit,
            COALESCE(
                ROUND(
                    COALESCE(
                        NULLIF(
                            REPLACE(
                                REGEXP_REPLACE(TRIM(raw->>'min_stock'), '[^0-9,.-]', '', 'g'),
                                ',',
                                '.'
                            ),
                            ''
                        )::NUMERIC,
                        5
                    )
                )::INTEGER,
                5
            ) AS min_stock,
            COALESCE(updated_at, CURRENT_TIMESTAMP) AS last_updated,
            COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at,
            CONCAT('Fuente: ', source) AS notes
        FROM "Stock"
        WHERE NULLIF(TRIM(raw->>'Producto'), '') IS NOT NULL
        ON CONFLICT (sku) DO UPDATE
        SET
            product_name = EXCLUDED.product_name,
            category = EXCLUDED.category,
            quantity = EXCLUDED.quantity,
            unit = EXCLUDED.unit,
            last_updated = EXCLUDED.last_updated,
            created_at = EXCLUDED.created_at,
            notes = EXCLUDED.notes;
    ELSE
        RAISE NOTICE 'Tabla "Stock" no encontrada. inventory mantendrá los datos existentes.';
    END IF;
END;
$$;

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

-- Tabla de consumos (Info Reserva -> descuenta inventario)
CREATE TABLE IF NOT EXISTS reservation_consumption (
    id SERIAL PRIMARY KEY,
    reservation_id INTEGER,
    item_sku VARCHAR(100),
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit VARCHAR(50) DEFAULT 'unidades',
    status VARCHAR(30) DEFAULT 'pending',
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL
);

-- Índices para acelerar el procesamiento de consumos pendientes
CREATE INDEX IF NOT EXISTS idx_reservation_consumption_processed ON reservation_consumption(processed_at, status);
CREATE INDEX IF NOT EXISTS idx_reservation_consumption_sku ON reservation_consumption(item_sku);
CREATE INDEX IF NOT EXISTS idx_reservation_consumption_name ON reservation_consumption(LOWER(item_name));


-- Crear trigger: al insertar en "Informacion Reservas", registrar consumos en reservation_consumption
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'Informacion Reservas'
    ) THEN
        -- Función que transforma claves de extras en consumos
        CREATE OR REPLACE FUNCTION fn_info_reservas_to_consumption()
        RETURNS trigger AS $fn$
        DECLARE
            v_raw jsonb;
            rec RECORD;
            v_qty_text TEXT;
            v_qty_int INTEGER;
            v_alias TEXT;
            v_name TEXT;
            v_sku VARCHAR(100);
        BEGIN
            -- Intentar parsear raw como JSONB
            BEGIN
                v_raw := NEW.raw::jsonb;
            EXCEPTION WHEN others THEN
                -- Si falla el parseo, no hacemos nada
                RETURN NEW;
            END;

            -- Iterar sobre cada clave/valor del JSON
            FOR rec IN
                SELECT key, value
                FROM jsonb_each(v_raw)
            LOOP
                -- Filtrar campos de consumo (extras, cervezas, tablas, bebidas_y_jugos, otros_alcoholes, cha)
                IF lower(rec.key) LIKE 'extras%%' 
                   OR lower(rec.key) LIKE 'cervezas%%'
                   OR lower(rec.key) LIKE 'tablas%%'
                   OR lower(rec.key) LIKE 'bebidas_y_jugos%%'
                   OR lower(rec.key) LIKE 'otros_alcoholes%%'
                   OR lower(rec.key) LIKE 'cha%%'
                THEN
                    -- valor puede venir como texto o número
                    IF jsonb_typeof(rec.value) = 'string' THEN
                        v_qty_text := rec.value::text;      -- con comillas
                        v_qty_text := trim(both '"' from v_qty_text); -- quitar comillas
                    ELSIF jsonb_typeof(rec.value) IN ('number', 'integer') THEN
                        v_qty_text := rec.value::text;
                    ELSE
                        v_qty_text := NULL;
                    END IF;

                    -- Normalizar cantidad a entero
                    IF v_qty_text IS NOT NULL AND length(trim(v_qty_text)) > 0 THEN
                        v_qty_text := regexp_replace(v_qty_text, '[^0-9.-]', '', 'g');
                        IF v_qty_text IS NOT NULL AND length(trim(v_qty_text)) > 0 THEN
                            BEGIN
                                v_qty_int := v_qty_text::int;
                            EXCEPTION WHEN others THEN
                                v_qty_int := 0;
                            END;
                        END IF;
                    END IF;

                    IF COALESCE(v_qty_int, 0) > 0 THEN
                        -- Extraer alias dentro de corchetes: extras_tipo_x_[alias]
                        v_alias := substring(rec.key from '\\[(.+)\\]');
                        IF v_alias IS NULL OR length(v_alias) = 0 THEN
                            -- Si no hay corchetes, usar la clave completa como alias
                            v_alias := rec.key;
                        END IF;
                        -- Transformar alias a nombre legible: 'cerveza_royal' -> 'Cerveza Royal'
                        v_name := initcap(replace(v_alias, '_', ' '));
                        
                        -- Mapear alias a SKU (actualizado con los productos de inventory)
                        v_sku := CASE lower(v_alias)
                            -- Cervezas
                            WHEN 'cerveza_austral_calafate' THEN 'CRV-AUCAL'
                            WHEN 'austral_calafate' THEN 'CRV-AUCAL'
                            WHEN 'cerveza_austral_lager' THEN 'CRV-AULAG'
                            WHEN 'austral_lager' THEN 'CRV-AULAG'
                            WHEN 'cerveza_kunstman_valdivia' THEN 'CRV-KUVAL'
                            WHEN 'kunstman_valdivia' THEN 'CRV-KUVAL'
                            WHEN 'cerveza_kunstman_torobayo' THEN 'CRV-KUTOR'
                            WHEN 'kunstman_torobayo' THEN 'CRV-KUTOR'
                            WHEN 'cerveza_artesanal_ambar' THEN 'CRV-ARTAMB'
                            WHEN 'artesanal_ambar' THEN 'CRV-ARTAMB'
                            WHEN 'cerveza_artesanal_negra' THEN 'CRV-ARTNEG'
                            WHEN 'artesanal_negra' THEN 'CRV-ARTNEG'
                            WHEN 'cerveza_royal' THEN 'CRV-ROYAL'
                            WHEN 'royal' THEN 'CRV-ROYAL'
                            -- Champaña
                            WHEN 'champaña_riccadonna_ruby' THEN 'CHP-RICRUBY'
                            WHEN 'riccadonna_ruby' THEN 'CHP-RICRUBY'
                            WHEN 'champaña_riccadonna_moscato_rose' THEN 'CHP-RICMROS'
                            WHEN 'riccadonna_moscato_rose' THEN 'CHP-RICMROS'
                            WHEN 'champaña_riccadonna_asti' THEN 'CHP-RICASTI'
                            WHEN 'riccadonna_asti' THEN 'CHP-RICASTI'
                            WHEN 'champaña_para_ramazotti' THEN 'CHP-RAMAZ'
                            WHEN 'para_ramazotti' THEN 'CHP-RAMAZ'
                            -- Licores
                            WHEN 'ramazotti' THEN 'LIC-RAMAZ'
                            WHEN 'lemon_stone' THEN 'LIC-LEMON'
                            WHEN 'lemon_stone_normal' THEN 'LIC-LEMON'
                            WHEN 'lemon stone' THEN 'LIC-LEMON'
                            WHEN 'maracuya_stone' THEN 'LIC-MARAC'
                            WHEN 'maracuya_stone_' THEN 'LIC-MARAC'
                            WHEN 'maracuya stone' THEN 'LIC-MARAC'
                            -- Vinos
                            WHEN 'vino_carmenere' THEN 'VIN-CARMEN'
                            WHEN 'carmenere' THEN 'VIN-CARMEN'
                            WHEN 'vino_cabernet_sauvignon' THEN 'VIN-CABSAU'
                            WHEN 'cabernet_sauvignon' THEN 'VIN-CABSAU'
                            WHEN 'cabernet sauvignon' THEN 'VIN-CABSAU'
                            WHEN 'vino_merlot' THEN 'VIN-MERLOT'
                            WHEN 'merlot' THEN 'VIN-MERLOT'
                            -- Bebidas y Jugos
                            WHEN 'coca-cola' THEN 'BEB-COCA'
                            WHEN 'coca_cola' THEN 'BEB-COCA'
                            WHEN 'coca cola' THEN 'BEB-COCA'
                            WHEN 'fanta' THEN 'BEB-FANTA'
                            WHEN 'jugo_mango_naranja' THEN 'JUG-MANNAR'
                            WHEN 'mango_naranja' THEN 'JUG-MANNAR'
                            WHEN 'jugo_naranja' THEN 'JUG-NARANJA'
                            WHEN 'naranja' THEN 'JUG-NARANJA'
                            WHEN 'jugo_berries' THEN 'JUG-BERRIES'
                            WHEN 'berries' THEN 'JUG-BERRIES'
                            -- Tablas
                            WHEN 'tabla_2_personas' THEN 'TBL-2P'
                            WHEN 'tabla_2' THEN 'TBL-2P'
                            WHEN 'tabla 2 personas' THEN 'TBL-2P'
                            WHEN 'tabla_4_personas' THEN 'TBL-4P'
                            WHEN 'tabla_4' THEN 'TBL-4P'
                            WHEN 'tabla 4 personas' THEN 'TBL-4P'
                            -- Extras
                            WHEN 'chalas' THEN 'EXT-CHALAS'
                            WHEN 'toalla' THEN 'EXT-TOALLA'
                            WHEN 'toalla_poncho' THEN 'EXT-TPONCHO'
                            WHEN 'toalla poncho' THEN 'EXT-TPONCHO'
                            WHEN 'modo_romantico' THEN 'EXT-ROMAN'
                            WHEN 'modo romantico' THEN 'EXT-ROMAN'
                            WHEN 'romantico' THEN 'EXT-ROMAN'
                            WHEN 'video_15_segundos' THEN 'EXT-VID15'
                            WHEN 'video_15' THEN 'EXT-VID15'
                            WHEN 'video 15 segundos' THEN 'EXT-VID15'
                            WHEN 'video_60_segundos' THEN 'EXT-VID60'
                            WHEN 'video_60' THEN 'EXT-VID60'
                            WHEN 'video 60 segundos' THEN 'EXT-VID60'
                            ELSE NULL
                        END;

                        -- Insertar el consumo "pending"
                        INSERT INTO reservation_consumption (
                            reservation_id,
                            item_sku,
                            item_name,
                            quantity,
                            unit,
                            status,
                            created_at
                        )
                        VALUES (
                            NEW.id::integer,     -- ID de la fila en "Informacion Reservas" (cast a integer)
                            v_sku,               -- SKU mapeado desde el alias
                            v_name,
                            v_qty_int,
                            'unidades',
                            'pending',
                            NOW()
                        );
                    END IF;
                END IF;
            END LOOP;

            RETURN NEW;
        END;
        $fn$ LANGUAGE plpgsql;

        -- Trigger AFTER INSERT sobre la tabla con espacio en el nombre
        DROP TRIGGER IF EXISTS trg_info_reservas_after_insert ON "Informacion Reservas";
        CREATE TRIGGER trg_info_reservas_after_insert
        AFTER INSERT ON "Informacion Reservas"
        FOR EACH ROW
        EXECUTE FUNCTION fn_info_reservas_to_consumption();
    ELSE
        RAISE NOTICE 'Tabla "Informacion Reservas" no encontrada; no se crea trigger de consumos.';
    END IF;
END;
$$;

