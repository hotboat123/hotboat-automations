"""
Monitor de Resumen Semanal y Mensual - Versión Simplificada
Lee de la tabla materializada reservas_con_extras
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, time as dt_time, date
import pytz
import calendar

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class WeeklyMonthlySummaryMonitor(BaseMonitor):
    """Envía resumen semanal los lunes y mensual el primer lunes del mes"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 300)
        report_time = config.get("report_time", "09:00")
        hour, minute = map(int, report_time.split(":"))
        self.report_time = dt_time(hour, minute)
        self.last_weekly_report_date = None
        self.last_monthly_report_date = None
        
        timezone_str = config.get("timezone", "America/Santiago")
        try:
            self.timezone = pytz.timezone(timezone_str)
        except:
            self.timezone = pytz.UTC
            logger.warning(f"⚠️ Zona horaria '{timezone_str}' no válida, usando UTC")
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info(f"📊 Monitor de Resumen Semanal/Mensual inicializado (envío: {self.report_time.strftime('%H:%M')} los lunes)")
    
    async def check(self) -> List[Dict[str, Any]]:
        """Verifica si es lunes y hora de enviar reporte"""
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)
        current_time = now_local.time()
        current_date = now_local.date()
        
        # Solo enviar los lunes
        if current_date.weekday() != 0:  # 0 = lunes
            return []
        
        # Verificar si es hora de enviar
        if not self._has_passed_report_time(current_time):
            return []
        
        results = []
        
        # Reporte semanal (siempre los lunes)
        if self.last_weekly_report_date != current_date:
            results.append({
                "type": "weekly",
                "date": current_date
            })
        
        # Reporte mensual (primer lunes del mes)
        if current_date.day <= 7 and self.last_monthly_report_date != current_date:
            results.append({
                "type": "monthly",
                "date": current_date
            })
        
        return results
    
    def _has_passed_report_time(self, current_time: dt_time) -> bool:
        """Determina si ya se alcanzó la hora de reporte"""
        if current_time.hour > self.report_time.hour:
            return True
        if current_time.hour == self.report_time.hour and current_time.minute >= self.report_time.minute:
            return True
        return False
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """Genera y envía los reportes según el tipo"""
        if not current_state:
            return
        
        for report_request in current_state:
            report_type = report_request.get("type")
            report_date = report_request.get("date")
            
            if report_type == "weekly":
                await self._generate_weekly_report(report_date)
                self.last_weekly_report_date = report_date
            elif report_type == "monthly":
                await self._generate_monthly_report(report_date)
                self.last_monthly_report_date = report_date
    
    async def _generate_weekly_report(self, current_date: date):
        """Genera reporte semanal"""
        logger.info("📊 Generando reporte semanal...")
        
        try:
            # Calcular rango de la semana pasada (lunes a domingo)
            last_monday = current_date - timedelta(days=7)
            last_sunday = last_monday + timedelta(days=6)
            
            # Obtener datos
            summary = await self._get_period_summary(last_monday, last_sunday)
            daily_data = await self._get_daily_breakdown(last_monday, last_sunday)
            
            # Enviar reporte
            await self._send_weekly_report(last_monday, last_sunday, summary, daily_data)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte semanal: {e}", exc_info=True)
    
    async def _generate_monthly_report(self, current_date: date):
        """Genera reporte mensual"""
        logger.info("📊 Generando reporte mensual...")
        
        try:
            # Calcular rango del mes pasado
            first_day_current = current_date.replace(day=1)
            last_day_previous = first_day_current - timedelta(days=1)
            first_day_previous = last_day_previous.replace(day=1)
            
            # Obtener datos
            summary = await self._get_period_summary(first_day_previous, last_day_previous)
            daily_data = await self._get_daily_breakdown(first_day_previous, last_day_previous)
            weekly_data = await self._get_weekly_breakdown(first_day_previous, last_day_previous)
            
            # Enviar reporte
            await self._send_monthly_report(
                first_day_previous, 
                last_day_previous, 
                summary, 
                daily_data,
                weekly_data
            )
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte mensual: {e}", exc_info=True)
    
    async def _get_period_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Obtiene resumen de un periodo desde reservas_con_extras"""
        query = """
            SELECT 
                COUNT(*) as total_reservas,
                COUNT(CASE WHEN tiene_cruce THEN 1 END) as reservas_con_info,
                COUNT(CASE WHEN NOT tiene_cruce THEN 1 END) as reservas_sin_info,
                COALESCE(SUM(ingreso_reserva), 0) as total_ingreso_reservas,
                COALESCE(SUM(ingreso_extras), 0) as total_ingreso_extras,
                COALESCE(SUM(ingreso_total), 0) as total_ingresos,
                COALESCE(SUM(costo_operativo_total), 0) as total_costos_operativos,
                COALESCE(AVG(ingreso_total), 0) as promedio_por_reserva,
                COUNT(DISTINCT fecha) as dias_con_reservas
            FROM reservas_con_extras
            WHERE fecha BETWEEN %s AND %s
        """
        
        result = await self.db.execute_single(query, (start_date, end_date))
        
        if not result:
            return self._empty_summary()
        
        return {
            'total_reservas': result['total_reservas'] or 0,
            'reservas_con_info': result['reservas_con_info'] or 0,
            'reservas_sin_info': result['reservas_sin_info'] or 0,
            'total_ingreso_reservas': float(result['total_ingreso_reservas'] or 0),
            'total_ingreso_extras': float(result['total_ingreso_extras'] or 0),
            'total_ingresos': float(result['total_ingresos'] or 0),
            'total_costos_operativos': float(result['total_costos_operativos'] or 0),
            'promedio_por_reserva': float(result['promedio_por_reserva'] or 0),
            'dias_con_reservas': result['dias_con_reservas'] or 0
        }
    
    async def _get_daily_breakdown(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Obtiene desglose diario"""
        query = """
            SELECT 
                fecha,
                COUNT(*) as num_reservas,
                COALESCE(SUM(ingreso_total), 0) as ingresos,
                COALESCE(SUM(costo_operativo_total), 0) as costos
            FROM reservas_con_extras
            WHERE fecha BETWEEN %s AND %s
            GROUP BY fecha
            ORDER BY fecha
        """
        
        try:
            rows = await self.db.execute_query(query, (start_date, end_date))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo desglose diario: {e}")
            return []
    
    async def _get_weekly_breakdown(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Obtiene desglose semanal para reporte mensual"""
        query = """
            SELECT 
                DATE_TRUNC('week', fecha) as semana,
                COUNT(*) as num_reservas,
                COALESCE(SUM(ingreso_total), 0) as ingresos,
                COALESCE(SUM(costo_operativo_total), 0) as costos
            FROM reservas_con_extras
            WHERE fecha BETWEEN %s AND %s
            GROUP BY DATE_TRUNC('week', fecha)
            ORDER BY semana
        """
        
        try:
            rows = await self.db.execute_query(query, (start_date, end_date))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo desglose semanal: {e}")
            return []
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Retorna resumen vacío"""
        return {
            'total_reservas': 0,
            'reservas_con_info': 0,
            'reservas_sin_info': 0,
            'total_ingreso_reservas': 0,
            'total_ingreso_extras': 0,
            'total_ingresos': 0,
            'total_costos_operativos': 0,
            'promedio_por_reserva': 0,
            'dias_con_reservas': 0
        }
    
    async def _send_weekly_report(
        self,
        start_date: date,
        end_date: date,
        summary: Dict[str, Any],
        daily_data: List[Dict[str, Any]]
    ):
        """Envía reporte semanal por email"""
        
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")
        
        utilidad = summary['total_ingresos'] - summary['total_costos_operativos']
        margen = (utilidad / summary['total_ingresos'] * 100) if summary['total_ingresos'] > 0 else 0
        
        message = f"""
📅 REPORTE SEMANAL - {start_str} al {end_str}

{'='*40}
📊 RESUMEN GENERAL

📅 Total Reservas: {summary['total_reservas']}
📝 Con Información: {summary['reservas_con_info']}
⚠️ Sin Información: {summary['reservas_sin_info']}
🗓️ Días con reservas: {summary['dias_con_reservas']}/7

{'='*40}
💰 INGRESOS

💵 Reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Extras: ${summary['total_ingreso_extras']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL: ${summary['total_ingresos']:,.0f}

📊 Promedio/reserva: ${summary['promedio_por_reserva']:,.0f}

{'='*40}
💸 COSTOS Y UTILIDAD

💸 Costos Operativos: ${summary['total_costos_operativos']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD: ${utilidad:,.0f}
📊 Margen: {margen:.1f}%

{'='*40}
📈 DESGLOSE DIARIO

"""
        
        # Agregar datos diarios
        for day_data in daily_data:
            fecha_str = day_data['fecha'].strftime("%d/%m")
            dia_semana = calendar.day_name[day_data['fecha'].weekday()]
            message += f"{fecha_str} ({dia_semana}): {day_data['num_reservas']} reservas - ${day_data['ingresos']:,.0f}\n"
        
        message += f"\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
        # Enviar
        try:
            sent = await self.send_notification(
                message=message,
                priority="high",
                channel="email"
            )
            if sent:
                logger.info("✅ Reporte semanal enviado por Email")
            else:
                logger.error("❌ No se pudo enviar el reporte semanal")
        except Exception as e:
            logger.error(f"❌ Error enviando reporte semanal: {e}")
    
    async def _send_monthly_report(
        self,
        start_date: date,
        end_date: date,
        summary: Dict[str, Any],
        daily_data: List[Dict[str, Any]],
        weekly_data: List[Dict[str, Any]]
    ):
        """Envía reporte mensual por email"""
        
        mes_nombre = calendar.month_name[start_date.month]
        year = start_date.year
        
        utilidad = summary['total_ingresos'] - summary['total_costos_operativos']
        margen = (utilidad / summary['total_ingresos'] * 100) if summary['total_ingresos'] > 0 else 0
        
        num_dias = (end_date - start_date).days + 1
        promedio_dia = summary['total_ingresos'] / num_dias if num_dias > 0 else 0
        
        message = f"""
📅 REPORTE MENSUAL - {mes_nombre} {year}

{'='*40}
📊 RESUMEN GENERAL

📅 Total Reservas: {summary['total_reservas']}
📝 Con Información: {summary['reservas_con_info']}
⚠️ Sin Información: {summary['reservas_sin_info']}
🗓️ Días con reservas: {summary['dias_con_reservas']}/{num_dias}

{'='*40}
💰 INGRESOS

💵 Reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Extras: ${summary['total_ingreso_extras']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL: ${summary['total_ingresos']:,.0f}

📊 Promedio/reserva: ${summary['promedio_por_reserva']:,.0f}
📅 Promedio/día: ${promedio_dia:,.0f}

{'='*40}
💸 COSTOS Y UTILIDAD

💸 Costos Operativos: ${summary['total_costos_operativos']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD: ${utilidad:,.0f}
📊 Margen: {margen:.1f}%

{'='*40}
📈 DESGLOSE SEMANAL

"""
        
        # Agregar datos semanales
        for idx, week_data in enumerate(weekly_data, 1):
            semana_start = week_data['semana']
            message += f"Semana {idx}: {week_data['num_reservas']} reservas - ${week_data['ingresos']:,.0f}\n"
        
        message += f"\n{'='*40}\n"
        message += f"📈 TOP 5 DÍAS DEL MES\n\n"
        
        # Top 5 días
        sorted_days = sorted(daily_data, key=lambda x: x['ingresos'], reverse=True)[:5]
        for idx, day_data in enumerate(sorted_days, 1):
            fecha_str = day_data['fecha'].strftime("%d/%m")
            message += f"{idx}. {fecha_str}: ${day_data['ingresos']:,.0f} ({day_data['num_reservas']} reservas)\n"
        
        message += f"\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
        # Enviar
        try:
            sent = await self.send_notification(
                message=message,
                priority="high",
                channel="email"
            )
            if sent:
                logger.info("✅ Reporte mensual enviado por Email")
            else:
                logger.error("❌ No se pudo enviar el reporte mensual")
        except Exception as e:
            logger.error(f"❌ Error enviando reporte mensual: {e}")
