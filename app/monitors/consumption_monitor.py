"""
Monitor de Consumos (Info Reserva → descuenta inventario)
"""
from typing import Dict, Any, Optional, List, Tuple

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class ConsumptionMonitor(BaseMonitor):
    """Procesa consumos registrados y descuenta stock en inventario"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        # Intervalo corto para procesar consumos rápido
        self.check_interval = config.get("check_interval", 30)
        # Tabla donde se registran consumos (alias de 'Info Reserva')
        self.table_name = config.get("table_name", "reservation_consumption")
        # Preferencia de canal para alertas inmediatas
        channel_preference = config.get("notification_channel", "whatsapp")
        self.notification_channel = None if channel_preference in (None, "all") else channel_preference
        # Límite de filas a procesar por ciclo para evitar picos
        self.batch_limit = config.get("batch_limit", 100)
    
    async def initialize(self):
        """Inicializa y habilita procesamiento desde el primer ciclo"""
        await super().initialize()
        # Forzar que detect_changes corra en el primer ciclo
        self.last_state = {}
    
    async def check(self) -> List[Dict[str, Any]]:
        """
        Obtiene consumos pendientes de procesar.
        """
        query = f"""
            SELECT
                id,
                reservation_id,
                COALESCE(item_sku, '') AS item_sku,
                item_name,
                quantity,
                COALESCE(unit, 'unidades') AS unit,
                created_at
            FROM {self.table_name}
            WHERE processed_at IS NULL
            ORDER BY created_at ASC, id ASC
            LIMIT %s
        """
        try:
            rows = await self.db.execute_query(query, (self.batch_limit,))
        except Exception as e:
            logger.error(f"❌ Error consultando consumos pendientes: {e}")
            return []
        
        if rows:
            logger.info(f"🧾 Consumptions pendientes: {len(rows)}")
        return rows
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """Procesa el lote de consumos pendientes"""
        if not current_state:
            return
        
        for consumption in current_state:
            try:
                await self._process_consumption(consumption)
            except Exception as e:
                logger.error(f"❌ Error procesando consumo {consumption.get('id')}: {e}", exc_info=True)
    
    async def _process_consumption(self, c: Dict[str, Any]) -> None:
        """
        Aplica un consumo al inventario y marca el registro como procesado.
        """
        consumption_id = c.get("id")
        item_sku = (c.get("item_sku") or "").strip()
        item_name = (c.get("item_name") or "").strip()
        amount = int(c.get("quantity") or 0)
        
        if amount <= 0:
            await self._mark_consumption_status(consumption_id, "skipped", note="Cantidad no positiva")
            logger.warning(f"⚠️ Consumo {consumption_id} omitido: cantidad inválida ({amount})")
            return
        
        inventory_item = await self._find_inventory_item(item_sku=item_sku, item_name=item_name)
        if not inventory_item:
            await self._mark_consumption_status(consumption_id, "error", note="Producto no encontrado en inventario")
            logger.warning(f"⚠️ Producto no encontrado para consumo {consumption_id}: sku='{item_sku}', nombre='{item_name}'")
            return
        
        inv_id = inventory_item["id"]
        product_name = inventory_item["product_name"]
        current_qty = int(inventory_item.get("quantity") or 0)
        min_stock = int(inventory_item.get("min_stock") or 0)
        unit = inventory_item.get("unit") or "unidades"
        
        new_qty = current_qty - amount
        if new_qty < 0:
            new_qty = 0
        
        rows = await self.db.execute_non_query(
            "UPDATE inventory SET quantity = %s WHERE id = %s",
            (new_qty, inv_id)
        )
        
        if rows <= 0:
            await self._mark_consumption_status(consumption_id, "error", note="No se pudo actualizar inventario")
            logger.error(f"❌ No se pudo actualizar inventario id={inv_id} para consumo {consumption_id}")
            return
        
        # Marcar consumo como procesado
        await self._mark_consumption_status(consumption_id, "processed", note=None)
        
        logger.info(
            f"✅ Descontado {amount} {unit} de '{product_name}' ({current_qty} → {new_qty})"
        )
        
        # Notificación inmediata si quedó bajo mínimo
        if new_qty <= min_stock:
            await self._notify_below_min(product_name, new_qty, min_stock, unit)
    
    async def _find_inventory_item(self, item_sku: str, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Busca un item en inventario por SKU o por nombre (case-insensitive).
        En caso de duplicados por nombre, prioriza filas con SKU definido.
        """
        # Intentar por SKU primero
        if item_sku:
            row = await self.db.execute_single(
                """
                SELECT id, product_name, sku, quantity, unit, min_stock
                FROM inventory
                WHERE sku = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (item_sku,)
            )
            if row:
                return row
        
        # Fallback: por nombre (case-insensitive), priorizando filas con SKU no nulo
        if item_name:
            row = await self.db.execute_single(
                """
                SELECT id, product_name, sku, quantity, unit, min_stock
                FROM inventory
                WHERE LOWER(product_name) = LOWER(%s)
                ORDER BY (sku IS NULL) ASC, id DESC
                LIMIT 1
                """,
                (item_name,)
            )
            if row:
                return row
        
        return None
    
    async def _mark_consumption_status(self, consumption_id: int, status: str, note: Optional[str]) -> None:
        """Marca un consumo con processed_at y estado"""
        await self.db.execute_non_query(
            """
            UPDATE {table}
            SET processed_at = NOW(),
                status = %s,
                note = %s
            WHERE id = %s
            """.format(table=self.table_name),
            (status, note, consumption_id)
        )
    
    async def _notify_below_min(self, product_name: str, qty: int, min_stock: int, unit: str) -> None:
        """Envía notificación inmediata cuando queda en o bajo stock mínimo"""
        message = f"""
🟡 Stock Bajo tras consumo

📦 Producto: {product_name}
📊 Cantidad actual: {qty} {unit}
📌 Stock mínimo: {min_stock} {unit}
➡️ Considera reabastecer
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="high",
            channel=self.notification_channel or "whatsapp"
        )


