"""
Monitor de Sincronización de Reservas con Extras → Google Sheets
Mantiene actualizada una hoja de Google Sheets con los datos de reservas_con_extras
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class ReservasSheetsSyncMonitor(BaseMonitor):
    """Sincroniza reservas_con_extras a Google Sheets"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 600)  # cada 10 minutos
        # Sincronizar solo desde hoy en adelante para no modificar fechas pasadas
        self.sync_from_today = config.get("sync_from_today", True)  
        self.last_sync_time = None
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info("🔄 Monitor de Sincronización Reservas → Sheets inicializado")
        if self.sync_from_today:
            logger.info("📊 Sincronizará solo fechas >= HOY (no modifica fechas pasadas)")
        else:
            logger.info("📊 Sincronizará todas las fechas")
    
    async def check(self) -> List[Dict[str, Any]]:
        """
        Obtiene reservas para sincronizar.
        Por defecto solo sincroniza desde HOY en adelante para no modificar fechas pasadas.
        """
        if self.sync_from_today:
            # Solo sincronizar desde hoy en adelante
            start_date = datetime.now().date()
            logger.debug(f"📅 Sincronizando solo desde {start_date} en adelante")
        else:
            # Sincronizar todo (modo legacy)
            start_date = datetime.now().date() - timedelta(days=365)
        
        query = """
            SELECT 
                id,
                appointment_id,
                reservation_id,
                fecha,
                hora,
                nombre_cliente,
                email,
                telefono,
                servicio,
                num_personas,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                costo_operativo_fijo,
                costo_operativo_variable,
                costo_operativo_total,
                num_adultos,
                num_ninos,
                ciudad_origen,
                como_supieron,
                clima_del_dia,
                categoria_clientes,
                tipo_clientes,
                status,
                tiene_cruce,
                extras_json,
                created_at,
                updated_at
            FROM reservas_con_extras
            WHERE fecha >= %s
            ORDER BY fecha DESC, hora DESC
        """
        
        try:
            rows = await self.db.execute_query(query, (start_date,))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error consultando reservas_con_extras: {e}")
            return []
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """
        Detecta cambios y sincroniza con la tabla intermedia para Google Sheets
        """
        if not current_state:
            logger.warning("⚠️ No hay datos de reservas para sincronizar")
            return
        
        logger.info(f"🔄 Sincronizando {len(current_state)} reservas con Google Sheets...")
        
        try:
            # Sincronizar a tabla intermedia
            await self._sync_to_sheets_table(current_state)
            
            self.last_sync_time = datetime.now()
            logger.info(f"✅ Sincronización completada: {len(current_state)} reservas actualizadas")
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}", exc_info=True)
    
    async def _sync_to_sheets_table(self, reservas: List[Dict[str, Any]]) -> None:
        """
        Sincroniza las reservas a una tabla intermedia que se conecta con Google Sheets.
        Solo actualiza/inserta registros de fechas >= HOY para no modificar fechas pasadas.
        """
        try:
            # NO limpiamos datos antiguos para mantener ediciones manuales
            # Solo sincronizamos fechas >= hoy
            
            success_count = 0
            error_count = 0
            
            for reserva in reservas:
                try:
                    await self._upsert_reserva_to_sheets(reserva)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error procesando reserva {reserva.get('appointment_id')}: {e}")
            
            logger.info(f"📊 Sincronización: {success_count} éxito, {error_count} errores")
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización a tabla Sheets: {e}", exc_info=True)
    
    async def _upsert_reserva_to_sheets(self, reserva: Dict[str, Any]) -> None:
        """
        Inserta o actualiza una reserva en la tabla intermedia de Google Sheets
        """
        # Construir el objeto JSON para Google Sheets
        sheets_data = {
            'id': str(reserva.get('id', '')),
            'appointment_id': str(reserva.get('appointment_id', '')),
            'reservation_id': str(reserva.get('reservation_id', '')),
            'fecha': reserva.get('fecha').strftime('%Y-%m-%d') if reserva.get('fecha') else '',
            'hora': reserva.get('hora').strftime('%H:%M:%S') if reserva.get('hora') else '',
            'nombre_cliente': reserva.get('nombre_cliente', ''),
            'email': reserva.get('email', ''),
            'telefono': reserva.get('telefono', ''),
            'servicio': reserva.get('servicio', ''),
            'num_personas': int(reserva.get('num_personas') or 0),
            'ingreso_reserva': float(reserva.get('ingreso_reserva') or 0),
            'ingreso_extras': float(reserva.get('ingreso_extras') or 0),
            'ingreso_total': float(reserva.get('ingreso_total') or 0),
            'costo_operativo_fijo': float(reserva.get('costo_operativo_fijo') or 0),
            'costo_operativo_variable': float(reserva.get('costo_operativo_variable') or 0),
            'costo_operativo_total': float(reserva.get('costo_operativo_total') or 0),
            'num_adultos': int(reserva.get('num_adultos') or 0),
            'num_ninos': int(reserva.get('num_ninos') or 0),
            'ciudad_origen': reserva.get('ciudad_origen', ''),
            'como_supieron': reserva.get('como_supieron', ''),
            'clima_del_dia': reserva.get('clima_del_dia', ''),
            'categoria_clientes': reserva.get('categoria_clientes', ''),
            'tipo_clientes': reserva.get('tipo_clientes', ''),
            'status': reserva.get('status', ''),
            'tiene_cruce': bool(reserva.get('tiene_cruce', False)),
            'extras_json': reserva.get('extras_json') or {},
        }
        
        # Upsert en la tabla de Google Sheets
        # Nota: Como usamos un índice único en lugar de constraint, 
        # necesitamos hacer insert y capturar el error de duplicado
        import json
        
        upsert_query = """
            INSERT INTO "Reservas_Con_Extras_Sheets" (raw, source, created_at, updated_at)
            VALUES (%s::jsonb, 'reservas_con_extras', NOW(), NOW())
            ON CONFLICT ON CONSTRAINT unique_reserva_sheets DO UPDATE SET
                raw = EXCLUDED.raw,
                updated_at = NOW()
        """
        
        try:
            await self.db.execute_non_query(upsert_query, (json.dumps(sheets_data),))
        except Exception as e:
            # Si falla por el constraint, intentar update directo
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                update_query = """
                    UPDATE "Reservas_Con_Extras_Sheets"
                    SET raw = %s::jsonb, updated_at = NOW()
                    WHERE raw->>'appointment_id' = %s AND raw->>'fecha' = %s
                """
                rows_affected = await self.db.execute_non_query(
                    update_query, 
                    (json.dumps(sheets_data), sheets_data['appointment_id'], sheets_data['fecha'])
                )
                
                # Si no existe, insertar
                if rows_affected == 0:
                    insert_query = """
                        INSERT INTO "Reservas_Con_Extras_Sheets" (raw, source, created_at, updated_at)
                        VALUES (%s::jsonb, 'reservas_con_extras', NOW(), NOW())
                    """
                    await self.db.execute_non_query(insert_query, (json.dumps(sheets_data),))
            else:
                raise
