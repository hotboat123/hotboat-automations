-- ============================================================================
-- Script de Verificación del Sistema de Inventario Automático
-- Ejecutar después de configurar el sistema para verificar que todo funciona
-- ============================================================================

SELECT '====================================================' as "";
SELECT 'VERIFICACIÓN DEL SISTEMA' as "";
SELECT '====================================================' as "";
SELECT '' as "";

-- ============================================================================
-- 1. Verificar que la tabla inventory existe y tiene productos
-- ============================================================================
SELECT '1. Verificando tabla inventory...' as "";

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM inventory;
    
    IF v_count = 0 THEN
        RAISE WARNING '⚠️  Tabla inventory existe pero está VACÍA';
        RAISE NOTICE '   Ejecutar: scripts/create_inventory_from_scratch.sql';
    ELSIF v_count < 31 THEN
        RAISE WARNING '⚠️  Tabla inventory tiene solo % productos (esperados: 31)', v_count;
    ELSE
        RAISE NOTICE '✅ Tabla inventory OK: % productos', v_count;
    END IF;
END $$;

-- Ver resumen por categoría
SELECT 
    '   ' || COALESCE(category, 'Sin categoría') as categoria,
    COUNT(*) as productos,
    SUM(quantity) as stock_total
FROM inventory 
GROUP BY category 
ORDER BY category;

SELECT '' as "";

-- ============================================================================
-- 2. Verificar que todos los productos tienen SKU único
-- ============================================================================
SELECT '2. Verificando SKUs únicos...' as "";

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count 
    FROM inventory 
    WHERE sku IS NULL OR sku = '';
    
    IF v_count > 0 THEN
        RAISE WARNING '⚠️  Hay % productos sin SKU', v_count;
    ELSE
        RAISE NOTICE '✅ Todos los productos tienen SKU único';
    END IF;
    
    -- Verificar duplicados (no debería haber por el UNIQUE constraint)
    SELECT COUNT(*) INTO v_count 
    FROM (
        SELECT sku, COUNT(*) 
        FROM inventory 
        WHERE sku IS NOT NULL 
        GROUP BY sku 
        HAVING COUNT(*) > 1
    ) t;
    
    IF v_count > 0 THEN
        RAISE WARNING '⚠️  Hay SKUs duplicados!';
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- 3. Verificar que la tabla reservation_consumption existe
-- ============================================================================
SELECT '3. Verificando tabla reservation_consumption...' as "";

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'reservation_consumption'
    ) THEN
        RAISE NOTICE '✅ Tabla reservation_consumption existe';
    ELSE
        RAISE WARNING '⚠️  Tabla reservation_consumption NO EXISTE';
        RAISE NOTICE '   Ejecutar: setup_database.sql';
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- 4. Verificar que el trigger existe
-- ============================================================================
SELECT '4. Verificando trigger automático...' as "";

DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'trg_info_reservas_after_insert'
    ) INTO v_exists;
    
    IF v_exists THEN
        RAISE NOTICE '✅ Trigger trg_info_reservas_after_insert existe';
        
        -- Verificar que la función existe
        IF EXISTS (
            SELECT 1 FROM pg_proc 
            WHERE proname = 'fn_info_reservas_to_consumption'
        ) THEN
            RAISE NOTICE '✅ Función fn_info_reservas_to_consumption existe';
        ELSE
            RAISE WARNING '⚠️  Función del trigger NO EXISTE';
        END IF;
    ELSE
        RAISE WARNING '⚠️  Trigger NO EXISTE';
        RAISE NOTICE '   Causa: La tabla "Informacion Reservas" no existe';
        RAISE NOTICE '   O no se ha ejecutado setup_database.sql';
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- 5. Verificar tabla "Informacion Reservas"
-- ============================================================================
SELECT '5. Verificando tabla "Informacion Reservas"...' as "";

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'Informacion Reservas'
    ) THEN
        SELECT COUNT(*) INTO v_count FROM "Informacion Reservas";
        RAISE NOTICE '✅ Tabla "Informacion Reservas" existe con % filas', v_count;
        
        -- Verificar que tiene columna raw
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'Informacion Reservas' AND column_name = 'raw'
        ) THEN
            RAISE NOTICE '✅ Columna "raw" existe';
        ELSE
            RAISE WARNING '⚠️  Columna "raw" NO EXISTE';
        END IF;
    ELSE
        RAISE WARNING '⚠️  Tabla "Informacion Reservas" NO EXISTE';
        RAISE NOTICE '   El trigger no se habrá creado';
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- 6. Verificar consumos pendientes
-- ============================================================================
SELECT '6. Verificando consumos pendientes...' as "";

DO $$
DECLARE
    v_pending INTEGER;
    v_processed INTEGER;
    v_error INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reservation_consumption') THEN
        SELECT COUNT(*) INTO v_pending FROM reservation_consumption WHERE status = 'pending';
        SELECT COUNT(*) INTO v_processed FROM reservation_consumption WHERE status = 'processed';
        SELECT COUNT(*) INTO v_error FROM reservation_consumption WHERE status = 'error';
        
        RAISE NOTICE '   Pendientes: %', v_pending;
        RAISE NOTICE '   Procesados: %', v_processed;
        RAISE NOTICE '   Con error: %', v_error;
        
        IF v_pending > 0 THEN
            RAISE NOTICE '⚠️  Hay % consumos pendientes de procesar', v_pending;
            RAISE NOTICE '   Verificar que ConsumptionMonitor esté ejecutándose';
        END IF;
        
        IF v_error > 0 THEN
            RAISE WARNING '⚠️  Hay % consumos con error', v_error;
            RAISE NOTICE '   Ver detalles: SELECT * FROM reservation_consumption WHERE status=''error'';';
        END IF;
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- 7. Verificar productos con stock bajo
-- ============================================================================
SELECT '7. Verificando stock bajo...' as "";

DO $$
DECLARE
    v_low INTEGER;
    v_out INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_low 
    FROM inventory 
    WHERE quantity > 0 AND quantity <= min_stock;
    
    SELECT COUNT(*) INTO v_out 
    FROM inventory 
    WHERE quantity = 0;
    
    IF v_out > 0 THEN
        RAISE WARNING '⚠️  Hay % productos SIN STOCK', v_out;
    END IF;
    
    IF v_low > 0 THEN
        RAISE WARNING '⚠️  Hay % productos con stock BAJO', v_low;
    END IF;
    
    IF v_out = 0 AND v_low = 0 THEN
        RAISE NOTICE '✅ Todo el stock está en niveles normales';
    END IF;
END $$;

-- Mostrar productos con stock bajo si los hay
SELECT 
    '   🔴 ' || product_name as producto,
    quantity as stock,
    min_stock as minimo
FROM inventory 
WHERE quantity = 0
LIMIT 5;

SELECT 
    '   🟡 ' || product_name as producto,
    quantity as stock,
    min_stock as minimo
FROM inventory 
WHERE quantity > 0 AND quantity <= min_stock
LIMIT 5;

SELECT '' as "";

-- ============================================================================
-- 8. Verificar índices
-- ============================================================================
SELECT '8. Verificando índices...' as "";

DO $$
DECLARE
    v_idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_idx_count
    FROM pg_indexes
    WHERE tablename IN ('inventory', 'reservation_consumption');
    
    RAISE NOTICE '✅ Hay % índices creados', v_idx_count;
END $$;

SELECT '' as "";

-- ============================================================================
-- 9. Verificar funciones de timestamp
-- ============================================================================
SELECT '9. Verificando funciones automáticas...' as "";

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'update_inventory_timestamp'
    ) THEN
        RAISE NOTICE '✅ Función update_inventory_timestamp existe';
    ELSE
        RAISE WARNING '⚠️  Función update_inventory_timestamp NO EXISTE';
    END IF;
END $$;

SELECT '' as "";

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================
SELECT '====================================================' as "";
SELECT 'RESUMEN DEL SISTEMA' as "";
SELECT '====================================================' as "";
SELECT '' as "";

DO $$
DECLARE
    v_inventory_count INTEGER;
    v_consumption_exists BOOLEAN;
    v_trigger_exists BOOLEAN;
    v_info_reservas_exists BOOLEAN;
    v_ready BOOLEAN := true;
BEGIN
    -- Checks
    SELECT COUNT(*) INTO v_inventory_count FROM inventory;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reservation_consumption') INTO v_consumption_exists;
    SELECT EXISTS (SELECT 1 FROM information_schema.triggers WHERE trigger_name = 'trg_info_reservas_after_insert') INTO v_trigger_exists;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'Informacion Reservas') INTO v_info_reservas_exists;
    
    -- Verificar cada componente
    IF v_inventory_count = 0 THEN
        RAISE NOTICE '❌ Tabla inventory vacía';
        v_ready := false;
    ELSE
        RAISE NOTICE '✅ Tabla inventory: % productos', v_inventory_count;
    END IF;
    
    IF NOT v_consumption_exists THEN
        RAISE NOTICE '❌ Tabla reservation_consumption no existe';
        v_ready := false;
    ELSE
        RAISE NOTICE '✅ Tabla reservation_consumption: OK';
    END IF;
    
    IF NOT v_info_reservas_exists THEN
        RAISE NOTICE '⚠️  Tabla "Informacion Reservas" no existe (trigger no creado)';
        RAISE NOTICE '   Esto es normal si aún no tienes esta tabla';
    ELSE
        RAISE NOTICE '✅ Tabla "Informacion Reservas": OK';
    END IF;
    
    IF v_info_reservas_exists AND NOT v_trigger_exists THEN
        RAISE NOTICE '❌ Trigger no existe (ejecutar setup_database.sql)';
        v_ready := false;
    ELSIF v_trigger_exists THEN
        RAISE NOTICE '✅ Trigger automático: OK';
    END IF;
    
    RAISE NOTICE '';
    
    IF v_ready THEN
        RAISE NOTICE '🎉 SISTEMA LISTO PARA PRODUCCIÓN';
        RAISE NOTICE '';
        RAISE NOTICE 'Siguiente paso:';
        RAISE NOTICE '  1. Iniciar el sistema: python main.py';
        RAISE NOTICE '  2. Verificar logs: tail -f logs/automation.log';
        RAISE NOTICE '  3. Crear una reserva de prueba';
    ELSE
        RAISE NOTICE '⚠️  SISTEMA INCOMPLETO';
        RAISE NOTICE '';
        RAISE NOTICE 'Ejecutar en orden:';
        IF v_inventory_count = 0 THEN
            RAISE NOTICE '  1. scripts/create_inventory_from_scratch.sql';
        END IF;
        IF NOT v_consumption_exists OR NOT v_trigger_exists THEN
            RAISE NOTICE '  2. setup_database.sql';
        END IF;
        RAISE NOTICE '  3. Verificar config.yaml (consumption.enabled: true)';
        RAISE NOTICE '  4. python main.py';
    END IF;
END $$;

SELECT '' as "";
SELECT '====================================================' as "";
SELECT 'Documentación completa en: scripts/RESUMEN_SISTEMA.md' as "";
SELECT '====================================================' as "";
