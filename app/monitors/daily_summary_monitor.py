"""
Monitor de Resumen Diario - Versión Simplificada
Lee de la tabla materializada reservas_con_extras
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, time as dt_time
from decimal import Decimal
import pytz

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class DailySummaryMonitor(BaseMonitor):
    """Envía resumen diario leyendo de reservas_con_extras"""
    
    # Ver BaseMonitor.start: permitir enviar en la primera iteración si ya es hora de reporte
    process_first_cycle_when_state_nonempty = True
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 300)
        report_time = config.get("report_time", "09:00")
        hour, minute = map(int, report_time.split(":"))
        self.report_time = dt_time(hour, minute)
        self.last_report_date = None
        
        timezone_str = config.get("timezone", "America/Santiago")
        try:
            self.timezone = pytz.timezone(timezone_str)
        except:
            self.timezone = pytz.UTC
            logger.warning(f"⚠️ Zona horaria '{timezone_str}' no válida, usando UTC")
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info(f"📊 Monitor de Resumen Diario inicializado (envío: {self.report_time.strftime('%H:%M')})")
    
    async def check(self) -> List[Dict[str, Any]]:
        """Verifica si es hora de enviar el reporte diario"""
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)
        current_time = now_local.time()
        current_date = now_local.date()
        
        if (self._has_passed_report_time(current_time) and
                self.last_report_date != current_date):
            
            logger.info(f"⏰ Es hora de enviar el reporte diario ({current_time.strftime('%H:%M')} {self.timezone})")
            self.last_report_date = current_date
            
            return [{"generate_report": True, "date": current_date}]
        
        return []
    
    def _has_passed_report_time(self, current_time: dt_time) -> bool:
        """Determina si ya se alcanzó la hora de reporte"""
        if current_time.hour > self.report_time.hour:
            return True
        if current_time.hour == self.report_time.hour and current_time.minute >= self.report_time.minute:
            return True
        return False
    
    def _yesterday_in_report_timezone(self):
        """
        Fecha del día que debe reportarse (ayer en la misma zona que report_time).
        Debe coincidir con lo que harías con: review_date_report.py YYYY-MM-DD
        para ese mismo "ayer" en Chile.
        """
        now_local = datetime.now(pytz.UTC).astimezone(self.timezone)
        return now_local.date() - timedelta(days=1)
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """Genera y envía el reporte diario"""
        if not current_state or not current_state[0].get("generate_report"):
            return
        
        logger.info("📊 Generando reporte diario...")
        
        try:
            # Ayer en America/Santiago (no usar datetime.now().date() del servidor: suele ser UTC en Railway)
            yesterday = self._yesterday_in_report_timezone()
            
            # Obtener datos desde la tabla reservas_con_extras
            summary_data = await self._get_daily_summary(yesterday)
            
            # Obtener costos de marketing
            marketing_cost = await self._get_marketing_cost(yesterday)
            
            # Generar y enviar el reporte
            await self._send_daily_report(yesterday, summary_data, marketing_cost)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte diario: {e}", exc_info=True)
    
    async def _get_daily_summary(self, date) -> Dict[str, Any]:
        """Obtiene resumen del día desde reservas_con_extras"""
        query = """
            SELECT 
                COUNT(*) as total_reservas,
                COUNT(CASE WHEN tiene_cruce THEN 1 END) as reservas_con_info,
                COUNT(CASE WHEN NOT tiene_cruce THEN 1 END) as reservas_sin_info,
                COALESCE(SUM(ingreso_reserva), 0) as total_ingreso_reservas,
                COALESCE(SUM(ingreso_extras), 0) as total_ingreso_extras,
                COALESCE(SUM(ingreso_total), 0) as total_ingresos,
                COALESCE(SUM(costo_operativo_fijo), 0) as total_costo_fijo,
                COALESCE(SUM(costo_operativo_variable), 0) as total_costo_variable,
                COALESCE(SUM(costo_operativo_total), 0) as total_costos_operativos,
                COALESCE(AVG(ingreso_total), 0) as promedio_por_reserva
            FROM reservas_con_extras
            WHERE fecha = %s
        """
        
        result = await self.db.execute_single(query, (date,))
        
        if not result:
            return {
                'total_reservas': 0,
                'reservas_con_info': 0,
                'reservas_sin_info': 0,
                'total_ingreso_reservas': 0,
                'total_ingreso_extras': 0,
                'total_ingresos': 0,
                'total_costo_fijo': 0,
                'total_costo_variable': 0,
                'total_costos_operativos': 0,
                'promedio_por_reserva': 0
            }
        
        return {
            'total_reservas': result['total_reservas'] or 0,
            'reservas_con_info': result['reservas_con_info'] or 0,
            'reservas_sin_info': result['reservas_sin_info'] or 0,
            'total_ingreso_reservas': float(result['total_ingreso_reservas'] or 0),
            'total_ingreso_extras': float(result['total_ingreso_extras'] or 0),
            'total_ingresos': float(result['total_ingresos'] or 0),
            'total_costo_fijo': float(result['total_costo_fijo'] or 0),
            'total_costo_variable': float(result['total_costo_variable'] or 0),
            'total_costos_operativos': float(result['total_costos_operativos'] or 0),
            'promedio_por_reserva': float(result['promedio_por_reserva'] or 0)
        }
    
    async def _get_marketing_cost(self, date) -> Dict[str, Any]:
        """Obtiene costos de marketing del día"""
        query = """
            SELECT 
                COALESCE(SUM(amount_spent), 0) as total_marketing,
                COUNT(*) as num_ads
            FROM marketing_costs
            WHERE cost_date = %s
        """
        
        try:
            result = await self.db.execute_single(query, (date,))
            if result:
                return {
                    'total_marketing': float(result['total_marketing'] or 0),
                    'num_ads': result['num_ads'] or 0
                }
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron obtener costos de marketing: {e}")
        
        return {'total_marketing': 0, 'num_ads': 0}
    
    async def _get_reservas_detalle(self, date, limit=8) -> List[Dict[str, Any]]:
        """Obtiene detalle de reservas del día"""
        query = """
            SELECT 
                hora,
                nombre_cliente,
                servicio,
                num_personas,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                extras_json,
                tiene_cruce
            FROM reservas_con_extras
            WHERE fecha = %s
            ORDER BY hora
            LIMIT %s
        """
        
        try:
            rows = await self.db.execute_query(query, (date, limit))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo detalle de reservas: {e}")
            return []
    
    async def _get_reservas_sin_info(self, date, limit=10) -> List[Dict[str, Any]]:
        """Obtiene reservas sin información completada"""
        query = """
            SELECT 
                hora,
                nombre_cliente,
                telefono,
                servicio
            FROM reservas_con_extras
            WHERE fecha = %s
              AND tiene_cruce = FALSE
            ORDER BY hora
            LIMIT %s
        """
        
        try:
            rows = await self.db.execute_query(query, (date, limit))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo reservas sin info: {e}")
            return []
    
    async def _send_daily_report(
        self, 
        date, 
        summary: Dict[str, Any],
        marketing: Dict[str, Any]
    ) -> None:
        """Envía el reporte diario por Email"""
        
        date_str = date.strftime("%d/%m/%Y")
        
        total_reservas = summary['total_reservas']
        reservas_con_info = summary['reservas_con_info']
        reservas_sin_info = summary['reservas_sin_info']
        
        # Determinar el estado
        if reservas_sin_info == 0:
            status_emoji = "✅"
            status_text = "TODAS COMPLETAS"
        elif reservas_sin_info < total_reservas / 2:
            status_emoji = "⚠️"
            status_text = "ALGUNAS FALTANTES"
        else:
            status_emoji = "🔴"
            status_text = "MUCHAS FALTANTES"
        
        # Calcular utilidades
        total_ingresos = summary['total_ingresos']
        total_costos_operativos = summary['total_costos_operativos']
        total_marketing = marketing['total_marketing']
        total_costos = total_costos_operativos + total_marketing
        utilidad_neta = total_ingresos - total_costos
        margen_neto = (utilidad_neta / total_ingresos * 100) if total_ingresos > 0 else 0
        
        # Construir mensaje
        message = f"""
{status_emoji} REPORTE DIARIO - {date_str}

📅 Reservas del día: {total_reservas}
📝 Información completada: {reservas_con_info}
{status_emoji} Faltantes: {reservas_sin_info}

Estado: {status_text}

{'='*40}
💰 INGRESOS DEL DÍA

💵 Total Reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Total Extras: ${summary['total_ingreso_extras']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${total_ingresos:,.0f}

📊 Promedio por reserva: ${summary['promedio_por_reserva']:,.0f}
🧾 Pagos registrados: {total_reservas}

{'='*40}
💸 COSTOS DEL DÍA

📢 Marketing: ${total_marketing:,.0f} ({marketing['num_ads']} anuncios)

🏭 Costos Operativos: ${total_costos_operativos:,.0f}
   Fijos ({total_reservas} reservas × $18,000):
     • Total: ${summary['total_costo_fijo']:,.0f}
   
   Variables (extras):
     • Total: ${summary['total_costo_variable']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: ${total_costos:,.0f}

{'='*40}
📈 UTILIDAD NETA

💰 Ingresos: ${total_ingresos:,.0f}
💸 Costos Totales: -${total_costos:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD NETA: ${utilidad_neta:,.0f}
📊 Margen Neto: {margen_neto:.1f}%
"""
        
        # Agregar detalle de reservas
        detalle = await self._get_reservas_detalle(date)
        if detalle:
            message += f"\n{'='*40}\n"
            message += "DETALLE POR RESERVA:\n\n"
            
            for idx, res in enumerate(detalle, 1):
                time_str = res['hora'].strftime("%H:%M") if res['hora'] else "N/A"
                message += f"{idx}. {time_str} - {res['nombre_cliente'] or 'Sin nombre'}\n"
                
                if res['num_personas']:
                    message += f"   👥 {res['num_personas']} personas\n"
                
                message += f"   💵 Subtotal Reserva: ${res['ingreso_reserva']:,.0f}\n"
                
                if res['ingreso_extras'] and res['ingreso_extras'] > 0:
                    message += f"   🍾 Extras: ${res['ingreso_extras']:,.0f}\n"
                    
                    # Mostrar algunos extras
                    if res['extras_json']:
                        extras_list = []
                        for nombre, cantidad in res['extras_json'].items():
                            extras_list.append(f"{cantidad}x {nombre}")
                        if extras_list:
                            message += f"      ({', '.join(extras_list[:3])})\n"
                
                message += f"   💰 Total: ${res['ingreso_total']:,.0f}\n\n"
            
            if total_reservas > len(detalle):
                message += f"... y {total_reservas - len(detalle)} reservas más.\n\n"
        
        # Agregar reservas sin información
        if reservas_sin_info > 0:
            faltantes = await self._get_reservas_sin_info(date)
            
            message += f"\n{'='*40}\n"
            message += "⚠️ RESERVAS SIN COMPLETAR:\n\n"
            
            for i, reserva in enumerate(faltantes, 1):
                time_str = reserva['hora'].strftime("%H:%M") if reserva['hora'] else "N/A"
                message += f"{i}. {time_str} - {reserva['nombre_cliente'] or 'Sin nombre'}\n"
                if reserva['telefono']:
                    message += f"   📞 {reserva['telefono']}\n"
                if reserva['servicio']:
                    message += f"   🚤 {reserva['servicio']}\n"
                message += "\n"
            
            if reservas_sin_info > len(faltantes):
                message += f"... y {reservas_sin_info - len(faltantes)} más.\n\n"
            
            message += "="*40 + "\n"
            message += "👉 Por favor, completar la información de estas reservas en el formulario."
        else:
            message += "\n🎉 ¡Excelente! Toda la información está completa."
        
        message += f"\n\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
        # Enviar por Email
        try:
            sent = await self.send_notification(
                message=message,
                priority="high",
                channel="email"
            )
            if sent:
                logger.info("✅ Reporte diario enviado por Email")
            else:
                logger.error("❌ No se pudo enviar el reporte diario")
                self.last_report_date = None
        except Exception as e:
            logger.error(f"❌ Error enviando reporte por Email: {e}")
            self.last_report_date = None
