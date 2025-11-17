"""
Monitor de Resumen Diario
Envía un reporte cada mañana comparando reservas vs información completada
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, time as dt_time
import asyncio

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class DailySummaryMonitor(BaseMonitor):
    """Envía resumen diario de reservas vs información completada"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        # Chequear cada 5 minutos si es hora de enviar el reporte
        self.check_interval = config.get("check_interval", 300)
        # Hora para enviar el reporte (por defecto 9:00 AM)
        report_time = config.get("report_time", "09:00")
        hour, minute = map(int, report_time.split(":"))
        self.report_time = dt_time(hour, minute)
        # Flag para saber si ya se envió hoy
        self.last_report_date = None
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info(f"📊 Monitor de Resumen Diario inicializado (envío: {self.report_time.strftime('%H:%M')})")
    
    async def check(self) -> List[Dict[str, Any]]:
        """
        Verifica si es hora de enviar el reporte diario
        """
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()
        
        # Verificar si es hora de enviar y no se ha enviado hoy
        if (current_time.hour == self.report_time.hour and 
            current_time.minute >= self.report_time.minute and
            self.last_report_date != current_date):
            
            # Marcar como enviado hoy
            self.last_report_date = current_date
            
            # Retornar datos para generar el reporte
            return [{"generate_report": True, "date": current_date}]
        
        return []
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """
        Genera y envía el reporte diario
        """
        if not current_state or not current_state[0].get("generate_report"):
            return
        
        logger.info("📊 Generando reporte diario...")
        
        try:
            # Obtener datos de ayer
            yesterday = datetime.now().date() - timedelta(days=1)
            
            # Contar reservas de ayer en appointments
            appointments_count = await self._count_appointments(yesterday)
            
            # Contar información completada de ayer
            info_reservas_count = await self._count_info_reservas(yesterday)
            
            # Obtener detalles de reservas sin información
            missing_details = await self._get_missing_reservas(yesterday)
            
            # Generar y enviar el mensaje
            await self._send_daily_report(
                yesterday,
                appointments_count,
                info_reservas_count,
                missing_details
            )
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte diario: {e}", exc_info=True)
    
    async def _count_appointments(self, date) -> int:
        """Cuenta las reservas de una fecha específica"""
        query = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE DATE(starts_at) = %s
              AND status NOT IN ('canceled', 'rejected')
        """
        
        try:
            result = await self.db.execute_single(query, (date,))
            return result.get('total', 0) if result else 0
        except Exception as e:
            logger.error(f"❌ Error contando appointments: {e}")
            return 0
    
    async def _count_info_reservas(self, date) -> int:
        """Cuenta las filas de información completada de una fecha específica"""
        query = """
            SELECT COUNT(*) as total
            FROM "Informacion Reservas"
            WHERE DATE(created_at) = %s
        """
        
        try:
            result = await self.db.execute_single(query, (date,))
            return result.get('total', 0) if result else 0
        except Exception as e:
            logger.error(f"❌ Error contando Informacion Reservas: {e}")
            return 0
    
    async def _get_missing_reservas(self, date) -> List[Dict[str, Any]]:
        """
        Obtiene detalles de las reservas que NO tienen información completada
        """
        query = """
            SELECT 
                a.id::text as appointment_id,
                a.starts_at,
                a.customer_name,
                a.raw->>'customer_phone_number' as phone,
                a.service_name
            FROM booknetic_appointments a
            WHERE DATE(a.starts_at) = %s
              AND a.status NOT IN ('canceled', 'rejected')
              AND NOT EXISTS (
                  SELECT 1 
                  FROM "Informacion Reservas" ir
                  WHERE DATE(ir.created_at) = %s
                    AND (
                        ir.raw->>'nombre_cliente' ILIKE '%%' || a.customer_name || '%%'
                        OR a.customer_name ILIKE '%%' || ir.raw->>'nombre_cliente' || '%%'
                    )
              )
            ORDER BY a.starts_at
        """
        
        try:
            rows = await self.db.execute_query(query, (date, date))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo reservas faltantes: {e}")
            return []
    
    async def _send_daily_report(
        self, 
        date, 
        appointments_count: int, 
        info_count: int,
        missing_details: List[Dict[str, Any]]
    ) -> None:
        """Envía el reporte diario por WhatsApp y Email"""
        
        date_str = date.strftime("%d/%m/%Y")
        missing_count = len(missing_details)
        
        # Determinar el estado
        if missing_count == 0:
            status_emoji = "✅"
            status_text = "TODAS COMPLETAS"
        elif missing_count < appointments_count / 2:
            status_emoji = "⚠️"
            status_text = "ALGUNAS FALTANTES"
        else:
            status_emoji = "🔴"
            status_text = "MUCHAS FALTANTES"
        
        # Construir mensaje
        message = f"""
{status_emoji} REPORTE DIARIO - {date_str}

📅 Reservas del día: {appointments_count}
📝 Información completada: {info_count}
{status_emoji} Faltantes: {missing_count}

Estado: {status_text}
"""
        
        # Añadir detalles de las faltantes
        if missing_details:
            message += "\n" + "="*40 + "\n"
            message += "⚠️ RESERVAS SIN COMPLETAR:\n\n"
            
            for i, reserva in enumerate(missing_details[:10], 1):  # Limitar a 10
                starts_at = reserva.get('starts_at')
                if isinstance(starts_at, str):
                    starts_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
                
                time_str = starts_at.strftime("%H:%M") if starts_at else "N/A"
                customer = reserva.get('customer_name', 'Sin nombre')
                phone = reserva.get('phone', 'Sin teléfono')
                service = reserva.get('service_name', 'Sin servicio')
                
                message += f"{i}. {time_str} - {customer}\n"
                message += f"   📞 {phone}\n"
                message += f"   🚤 {service}\n\n"
            
            if missing_count > 10:
                message += f"... y {missing_count - 10} más.\n\n"
            
            message += "="*40 + "\n"
            message += "👉 Por favor, completar la información de estas reservas en el formulario."
        else:
            message += "\n🎉 ¡Excelente! Toda la información está completa."
        
        message += f"\n\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
        # Enviar por WhatsApp
        try:
            await self.send_notification(
                message=message,
                priority="high",
                channel="whatsapp"
            )
            logger.info("✅ Reporte diario enviado por WhatsApp")
        except Exception as e:
            logger.error(f"❌ Error enviando reporte por WhatsApp: {e}")
        
        # Enviar por Email
        try:
            await self.send_notification(
                message=message,
                priority="high",
                channel="email"
            )
            logger.info("✅ Reporte diario enviado por Email")
        except Exception as e:
            logger.error(f"❌ Error enviando reporte por Email: {e}")

