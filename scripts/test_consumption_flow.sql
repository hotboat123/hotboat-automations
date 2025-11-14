-- Script de prueba para verificar el flujo completo:
-- Información Reservas → reservation_consumption → actualización de stock

-- ============================================================================
-- PASO 1: Verificar estado inicial del inventario
-- ============================================================================
SELECT 
    '=== ESTADO INICIAL DEL INVENTARIO ===' as info;

SELECT id, product_name, sku, quantity, min_stock 
FROM inventory 
WHERE sku IN ('CRV-ROYAL', 'BEB-COCA', 'TBL-2P', 'EXT-TOALLA')
ORDER BY sku;

-- ============================================================================
-- PASO 2: Simular una inserción en "Informacion Reservas"
-- ============================================================================
-- NOTA: Esto solo funcionará si la tabla "Informacion Reservas" existe
-- Si no existe, el trigger no se habrá creado y este test no aplicará

DO $$
BEGIN
    -- Verificar si existe la tabla "Informacion Reservas"
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'Informacion Reservas'
    ) THEN
        -- Insertar una reserva de prueba con varios productos
        INSERT INTO "Informacion Reservas" (raw, created_at, updated_at)
        VALUES (
            jsonb_build_object(
                'nombre_cliente', 'Test Usuario',
                'fecha_reserva', '2025-11-15',
                'extras_tipo_1_[cerveza_royal]', '2',
                'bebidas_y_jugos_tipo_1_[coca_cola]', '3',
                'tablas_[tabla_2_personas]', '1',
                'extras_tipo_2_[toalla]', '4'
            ),
            NOW(),
            NOW()
        );
        
        RAISE NOTICE '✅ Inserción de prueba realizada en "Informacion Reservas"';
    ELSE
        RAISE NOTICE '⚠️ Tabla "Informacion Reservas" no existe - omitiendo test';
    END IF;
END;
$$;

-- ============================================================================
-- PASO 3: Verificar que se crearon registros en reservation_consumption
-- ============================================================================
SELECT 
    '=== CONSUMOS CREADOS (PENDING) ===' as info;

SELECT 
    id,
    reservation_id,
    item_sku,
    item_name,
    quantity,
    status,
    created_at
FROM reservation_consumption
WHERE status = 'pending'
ORDER BY created_at DESC, id DESC
LIMIT 10;

-- ============================================================================
-- PASO 4: Información sobre el monitor de consumos
-- ============================================================================
SELECT 
    '=== INFORMACIÓN IMPORTANTE ===' as info;

SELECT 
    'El ConsumptionMonitor debe estar ejecutándose para procesar los consumos pendientes.' as nota
UNION ALL
SELECT 
    'Los consumos se procesarán automáticamente cada 30 segundos (configurable).' as nota
UNION ALL
SELECT 
    'Una vez procesados, el stock en inventory se actualizará automáticamente.' as nota;

-- ============================================================================
-- PASO 5: Consulta para verificar consumos procesados (ejecutar después)
-- ============================================================================
-- Descomenta estas líneas después de que el monitor haya procesado los consumos:

/*
SELECT 
    '=== CONSUMOS PROCESADOS ===' as info;

SELECT 
    id,
    reservation_id,
    item_sku,
    item_name,
    quantity,
    status,
    processed_at
FROM reservation_consumption
WHERE status = 'processed'
ORDER BY processed_at DESC
LIMIT 10;

SELECT 
    '=== ESTADO FINAL DEL INVENTARIO ===' as info;

SELECT id, product_name, sku, quantity, min_stock 
FROM inventory 
WHERE sku IN ('CRV-ROYAL', 'BEB-COCA', 'TBL-2P', 'EXT-TOALLA')
ORDER BY sku;
*/

-- ============================================================================
-- LIMPIEZA (OPCIONAL): Eliminar datos de prueba
-- ============================================================================
/*
-- Descomenta estas líneas para limpiar los datos de prueba:

DELETE FROM reservation_consumption 
WHERE reservation_id = (
    SELECT MAX(id) FROM "Informacion Reservas" 
    WHERE raw->>'nombre_cliente' = 'Test Usuario'
);

DELETE FROM "Informacion Reservas"
WHERE raw->>'nombre_cliente' = 'Test Usuario';

-- Restaurar cantidades en inventory si es necesario:
UPDATE inventory SET quantity = quantity + 2 WHERE sku = 'CRV-ROYAL';
UPDATE inventory SET quantity = quantity + 3 WHERE sku = 'BEB-COCA';
UPDATE inventory SET quantity = quantity + 1 WHERE sku = 'TBL-2P';
UPDATE inventory SET quantity = quantity + 4 WHERE sku = 'EXT-TOALLA';
*/

