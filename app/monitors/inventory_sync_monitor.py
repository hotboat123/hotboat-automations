"""
Monitor de Sincronización de Inventory → Google Sheets
Mantiene actualizada la hoja "Stock" en Google Sheets con los cambios de inventory
"""
from typing import Dict, Any, List
from datetime import datetime

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class InventorySyncMonitor(BaseMonitor):
    """Sincroniza cambios de inventory de vuelta a Google Sheets"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 300)  # cada 5 minutos por defecto
        self.table_name = "inventory"
        self.last_sync = {}
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info("🔄 Monitor de Sincronización de Inventory inicializado")
    
    async def check(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los productos de inventory para sincronizar
        """
        query = """
            SELECT 
                id,
                product_name,
                sku,
                category,
                quantity,
                unit,
                min_stock,
                last_updated
            FROM inventory
            ORDER BY sku
        """
        
        try:
            rows = await self.db.execute_query(query)
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error consultando inventory: {e}")
            return []
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """
        Detecta cambios en inventory y sincroniza con Google Sheets
        """
        if not current_state:
            return
        
        # Detectar productos que cambiaron desde la última sincronización
        changes = []
        
        for item in current_state:
            sku = item.get('sku')
            if not sku:
                continue
            
            last_updated = item.get('last_updated')
            quantity = item.get('quantity', 0)
            
            # Verificar si cambió desde la última vez
            if sku not in self.last_sync or self.last_sync[sku]['quantity'] != quantity:
                changes.append(item)
                self.last_sync[sku] = {
                    'quantity': quantity,
                    'last_updated': last_updated
                }
        
        if changes:
            logger.info(f"🔄 Sincronizando {len(changes)} productos con Google Sheets...")
            await self._sync_to_sheets(changes)
    
    async def _sync_to_sheets(self, items: List[Dict[str, Any]]) -> None:
        """
        Sincroniza los cambios a la tabla Stock en la base de datos
        (hotboat-etl se encargará de subirlo a Google Sheets)
        """
        try:
            for item in items:
                sku = item.get('sku')
                product_name = item.get('product_name')
                quantity = item.get('quantity', 0)
                min_stock = item.get('min_stock', 5)
                category = item.get('category', '')
                
                # Actualizar la tabla Stock (que luego se sincroniza con Google Sheets)
                update_query = """
                    UPDATE "Stock"
                    SET raw = jsonb_set(
                        COALESCE(raw, '{}'::jsonb),
                        '{Stock}',
                        to_jsonb(%s::text)
                    ),
                    updated_at = NOW()
                    WHERE raw->>'id' = %s
                """
                
                try:
                    affected = await self.db.execute_non_query(
                        update_query,
                        (str(quantity), sku)
                    )
                    
                    if affected > 0:
                        logger.info(f"✅ Sincronizado: {product_name} ({sku}) → {quantity} unidades")
                    else:
                        # Si no existe en Stock, insertarlo
                        await self._insert_to_stock(item)
                        
                except Exception as e:
                    logger.error(f"❌ Error actualizando {sku} en Stock: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización a Google Sheets: {e}", exc_info=True)
    
    async def _insert_to_stock(self, item: Dict[str, Any]) -> None:
        """
        Inserta un nuevo producto en la tabla Stock si no existe
        """
        try:
            sku = item.get('sku')
            product_name = item.get('product_name')
            quantity = item.get('quantity', 0)
            min_stock = item.get('min_stock', 5)
            category = item.get('category', '')
            
            insert_query = """
                INSERT INTO "Stock" (raw, source, created_at, updated_at)
                VALUES (
                    jsonb_build_object(
                        'id', %s,
                        'Producto', %s,
                        'Stock', %s,
                        'min_stock', %s,
                        'Categoría', %s
                    ),
                    'inventory_sync',
                    NOW(),
                    NOW()
                )
                ON CONFLICT DO NOTHING
            """
            
            await self.db.execute_non_query(
                insert_query,
                (sku, product_name, str(quantity), str(min_stock), category)
            )
            
            logger.info(f"✅ Insertado nuevo producto en Stock: {product_name} ({sku})")
            
        except Exception as e:
            logger.error(f"❌ Error insertando producto en Stock: {e}")

