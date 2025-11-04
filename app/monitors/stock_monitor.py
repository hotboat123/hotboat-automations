"""
Monitor de Stock (Inventario)
"""
from typing import Dict, List, Any
from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class StockMonitor(BaseMonitor):
    """Monitorea niveles de stock/inventario"""
    
    async def check(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del inventario
        """
        # Query para obtener información de inventario
        # Nota: Ajusta esta query según tu esquema de base de datos
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
            ORDER BY product_name
        """
        
        try:
            inventory_items = await self.db.execute_query(query)
        except Exception as e:
            # Si la tabla no existe aún, retornar vacío
            logger.warning(f"⚠️ No se pudo consultar inventario: {e}")
            return {}
        
        # Crear diccionario indexado por ID
        inventory_dict = {
            str(item['id']): item for item in inventory_items
        }
        
        logger.debug(f"📦 {len(inventory_items)} productos en inventario")
        
        return inventory_dict
    
    async def detect_changes(self, current_state: Dict[str, Any]) -> None:
        """
        Detecta cambios en el inventario y envía notificaciones
        """
        if self.last_state is None:
            # Primera ejecución: verificar niveles actuales
            await self._check_current_levels(current_state)
            return
        
        # Verificar cambios en productos existentes
        for item_id, current_item in current_state.items():
            last_item = self.last_state.get(item_id)
            
            if last_item:
                await self._check_stock_change(last_item, current_item)
            else:
                # Nuevo producto
                logger.info(f"➕ Nuevo producto agregado: {current_item.get('product_name')}")
        
        # Productos eliminados
        for item_id in self.last_state:
            if item_id not in current_state:
                logger.info(f"➖ Producto eliminado del inventario: {self.last_state[item_id].get('product_name')}")
    
    async def _check_current_levels(self, inventory: Dict[str, Any]):
        """
        Verifica los niveles actuales de stock (primera ejecución)
        """
        thresholds = self.config.get('thresholds', {})
        low_stock_threshold = thresholds.get('low_stock', 5)
        critical_stock_threshold = thresholds.get('critical_stock', 2)
        
        low_stock_items = []
        critical_stock_items = []
        out_of_stock_items = []
        
        for item in inventory.values():
            quantity = item.get('quantity', 0)
            product_name = item.get('product_name', 'N/A')
            min_stock = item.get('min_stock', low_stock_threshold)
            
            if quantity == 0:
                out_of_stock_items.append(product_name)
            elif quantity <= critical_stock_threshold or quantity <= min_stock / 2:
                critical_stock_items.append(f"{product_name} (quedan {quantity})")
            elif quantity <= low_stock_threshold or quantity <= min_stock:
                low_stock_items.append(f"{product_name} (quedan {quantity})")
        
        # Enviar notificación de resumen inicial si hay items con stock bajo
        if out_of_stock_items or critical_stock_items or low_stock_items:
            message = "📦 **Resumen de Stock Inicial**\n\n"
            
            if out_of_stock_items:
                message += "🔴 **Sin Stock:**\n"
                message += "\n".join(f"• {item}" for item in out_of_stock_items)
                message += "\n\n"
            
            if critical_stock_items:
                message += "🟠 **Stock Crítico:**\n"
                message += "\n".join(f"• {item}" for item in critical_stock_items)
                message += "\n\n"
            
            if low_stock_items:
                message += "🟡 **Stock Bajo:**\n"
                message += "\n".join(f"• {item}" for item in low_stock_items)
            
            priority = "critical" if out_of_stock_items else "high" if critical_stock_items else "medium"
            
            await self.send_notification(
                message=message.strip(),
                priority=priority,
                channel="telegram"
            )
    
    async def _check_stock_change(self, last_item: Dict, current_item: Dict):
        """
        Verifica cambios en un producto específico
        """
        last_qty = last_item.get('quantity', 0)
        current_qty = current_item.get('quantity', 0)
        product_name = current_item.get('product_name', 'N/A')
        
        if last_qty == current_qty:
            return  # No hay cambio
        
        thresholds = self.config.get('thresholds', {})
        low_stock_threshold = thresholds.get('low_stock', 5)
        critical_stock_threshold = thresholds.get('critical_stock', 2)
        min_stock = current_item.get('min_stock', low_stock_threshold)
        
        # Detectar transiciones importantes
        
        # Stock se acabó
        if current_qty == 0 and last_qty > 0:
            if self.config.get('notifications', {}).get('out_of_stock', True):
                await self._notify_out_of_stock(current_item, last_qty)
        
        # Stock llegó a nivel crítico
        elif current_qty <= critical_stock_threshold and last_qty > critical_stock_threshold:
            if self.config.get('notifications', {}).get('critical_stock', True):
                await self._notify_critical_stock(current_item)
        
        # Stock llegó a nivel bajo
        elif current_qty <= low_stock_threshold and last_qty > low_stock_threshold:
            if self.config.get('notifications', {}).get('low_stock', True):
                await self._notify_low_stock(current_item)
        
        # Stock se restauró
        elif current_qty > min_stock and last_qty <= min_stock:
            if self.config.get('notifications', {}).get('stock_restored', True):
                await self._notify_stock_restored(current_item, last_qty, current_qty)
        
        # Cambio significativo (más del 50% de cambio)
        elif abs(current_qty - last_qty) / max(last_qty, 1) > 0.5:
            change_type = "aumentó" if current_qty > last_qty else "disminuyó"
            logger.info(
                f"📊 Stock de {product_name} {change_type} significativamente: "
                f"{last_qty} → {current_qty}"
            )
    
    async def _notify_out_of_stock(self, item: Dict, last_qty: int):
        """Notifica cuando un producto se queda sin stock"""
        message = f"""
🔴 **PRODUCTO SIN STOCK**

📦 Producto: {item.get('product_name', 'N/A')}
🏷️ SKU: {item.get('sku', 'N/A')}
📂 Categoría: {item.get('category', 'N/A')}
📊 Cantidad anterior: {last_qty} {item.get('unit', 'unidades')}
⚠️ **REQUIERE REPOSICIÓN URGENTE**
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="critical",
            channel="telegram"
        )
        
        logger.warning(f"🔴 SIN STOCK: {item.get('product_name')}")
    
    async def _notify_critical_stock(self, item: Dict):
        """Notifica cuando el stock llega a nivel crítico"""
        message = f"""
🟠 **STOCK CRÍTICO**

📦 Producto: {item.get('product_name', 'N/A')}
🏷️ SKU: {item.get('sku', 'N/A')}
📊 Cantidad actual: {item.get('quantity', 0)} {item.get('unit', 'unidades')}
⚠️ Por favor, reabastecer pronto
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="high",
            channel="telegram"
        )
        
        logger.warning(f"🟠 STOCK CRÍTICO: {item.get('product_name')} ({item.get('quantity')})")
    
    async def _notify_low_stock(self, item: Dict):
        """Notifica cuando el stock está bajo"""
        message = f"""
🟡 **Stock Bajo**

📦 Producto: {item.get('product_name', 'N/A')}
📊 Cantidad actual: {item.get('quantity', 0)} {item.get('unit', 'unidades')}
📌 Stock mínimo recomendado: {item.get('min_stock', 'N/A')}
ℹ️ Considera reabastecer
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="medium",
            channel="telegram"
        )
        
        logger.info(f"🟡 STOCK BAJO: {item.get('product_name')} ({item.get('quantity')})")
    
    async def _notify_stock_restored(self, item: Dict, last_qty: int, current_qty: int):
        """Notifica cuando el stock se ha restaurado"""
        message = f"""
✅ **Stock Restaurado**

📦 Producto: {item.get('product_name', 'N/A')}
📊 Cantidad: {last_qty} → {current_qty} {item.get('unit', 'unidades')}
👍 Stock restaurado a niveles normales
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="low",
            channel="telegram"
        )
        
        logger.info(f"✅ STOCK RESTAURADO: {item.get('product_name')} ({current_qty})")

