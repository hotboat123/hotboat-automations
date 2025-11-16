-- Script para corregir el trigger y el tipo de dato de reservation_id
-- Este script se ejecutará automáticamente al iniciar la app

-- Paso 1: Eliminar el trigger existente
DROP TRIGGER IF EXISTS trg_info_reservas_after_insert ON "Informacion Reservas";

-- Paso 2: Eliminar la función existente
DROP FUNCTION IF EXISTS fn_info_reservas_to_consumption();

-- Paso 3: Cambiar el tipo de dato de reservation_id a VARCHAR (acepta texto e IDs)
ALTER TABLE reservation_consumption 
ALTER COLUMN reservation_id TYPE VARCHAR(255);

CREATE FUNCTION fn_info_reservas_to_consumption()
RETURNS trigger AS $$
DECLARE
    v_raw jsonb;
    rec RECORD;
    v_qty_text TEXT;
    v_qty_int INTEGER;
    v_alias TEXT;
    v_name TEXT;
    v_sku VARCHAR(100);
BEGIN
    BEGIN
        v_raw := NEW.raw::jsonb;
    EXCEPTION WHEN others THEN
        RETURN NEW;
    END;

    FOR rec IN
        SELECT key, value
        FROM jsonb_each(v_raw)
    LOOP
        IF lower(rec.key) LIKE 'extras%' 
           OR lower(rec.key) LIKE 'cervezas%'
           OR lower(rec.key) LIKE 'tablas%'
           OR lower(rec.key) LIKE 'bebidas_y_jugos%'
           OR lower(rec.key) LIKE 'otros_alcoholes%'
           OR lower(rec.key) LIKE 'cha%'
        THEN
            IF jsonb_typeof(rec.value) = 'string' THEN
                v_qty_text := rec.value::text;
                v_qty_text := trim(both '"' from v_qty_text);
            ELSIF jsonb_typeof(rec.value) IN ('number', 'integer') THEN
                v_qty_text := rec.value::text;
            ELSE
                v_qty_text := NULL;
            END IF;

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
                v_alias := substring(rec.key from '\[(.+)\]');
                IF v_alias IS NULL OR length(v_alias) = 0 THEN
                    v_alias := rec.key;
                END IF;
                v_name := initcap(replace(v_alias, '_', ' '));
                
                v_sku := CASE lower(v_alias)
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
                    WHEN 'champaña_riccadonna_ruby' THEN 'CHP-RICRUBY'
                    WHEN 'riccadonna_ruby' THEN 'CHP-RICRUBY'
                    WHEN 'champaña_riccadonna_moscato_rose' THEN 'CHP-RICMROS'
                    WHEN 'riccadonna_moscato_rose' THEN 'CHP-RICMROS'
                    WHEN 'champaña_riccadonna_asti' THEN 'CHP-RICASTI'
                    WHEN 'riccadonna_asti' THEN 'CHP-RICASTI'
                    WHEN 'champaña_para_ramazotti' THEN 'CHP-RAMAZ'
                    WHEN 'para_ramazotti' THEN 'CHP-RAMAZ'
                    WHEN 'ramazotti' THEN 'LIC-RAMAZ'
                    WHEN 'lemon_stone' THEN 'LIC-LEMON'
                    WHEN 'lemon_stone_normal' THEN 'LIC-LEMON'
                    WHEN 'lemon stone' THEN 'LIC-LEMON'
                    WHEN 'maracuya_stone' THEN 'LIC-MARAC'
                    WHEN 'maracuya_stone_' THEN 'LIC-MARAC'
                    WHEN 'maracuya stone' THEN 'LIC-MARAC'
                    WHEN 'vino_carmenere' THEN 'VIN-CARMEN'
                    WHEN 'carmenere' THEN 'VIN-CARMEN'
                    WHEN 'vino_cabernet_sauvignon' THEN 'VIN-CABSAU'
                    WHEN 'cabernet_sauvignon' THEN 'VIN-CABSAU'
                    WHEN 'cabernet sauvignon' THEN 'VIN-CABSAU'
                    WHEN 'vino_merlot' THEN 'VIN-MERLOT'
                    WHEN 'merlot' THEN 'VIN-MERLOT'
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
                    WHEN 'tabla_2_personas' THEN 'TBL-2P'
                    WHEN 'tabla_2' THEN 'TBL-2P'
                    WHEN 'tabla 2 personas' THEN 'TBL-2P'
                    WHEN 'tabla_4_personas' THEN 'TBL-4P'
                    WHEN 'tabla_4' THEN 'TBL-4P'
                    WHEN 'tabla 4 personas' THEN 'TBL-4P'
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
                    NEW.id::text,
                    v_sku,
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
$$ LANGUAGE plpgsql;

-- Recrear el trigger
CREATE TRIGGER trg_info_reservas_after_insert
AFTER INSERT ON "Informacion Reservas"
FOR EACH ROW
EXECUTE FUNCTION fn_info_reservas_to_consumption();

