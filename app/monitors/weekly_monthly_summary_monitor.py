"""
Monitor de Resumen Semanal y Mensual - Versión Simplificada
Lee de la tabla all_appointments (solo status = confirmed)
"""
from collections import defaultdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, time as dt_time, date
import pytz
import calendar

from app.monitors.base_monitor import BaseMonitor
from app.monitors.extras_json_split import aggregate_financial_rows
from app.utils.extras_pricing import fetch_precios_extras_costs_dict
from app.utils.marketing_costs import fetch_marketing_for_period
from app.utils.meta_ads_analysis import fetch_and_analyze as fetch_meta_analysis
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
        self.costo_fijo_diario_prorrateado = float(config.get("costo_fijo_diario_prorrateado", 650_000))
        self.costo_operativo_fijo_por_reserva = float(config.get("costo_operativo_fijo_por_reserva", 18_000))
        self._precios_costs_cache = None
        
        timezone_str = config.get("timezone", "America/Santiago")
        try:
            self.timezone = pytz.timezone(timezone_str)
        except Exception:
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
        
        # Mismo criterio que el diario: leer de nuevo "Precios Extras" en cada ciclo de informes
        self._precios_costs_cache = None
        
        for report_request in current_state:
            report_type = report_request.get("type")
            report_date = report_request.get("date")
            start_date = report_request.get("start_date")
            end_date = report_request.get("end_date")
            
            if report_type == "weekly":
                if start_date and end_date:
                    await self._generate_weekly_report_with_dates(start_date, end_date)
                elif report_date:
                    await self._generate_weekly_report(report_date)
                else:
                    logger.error("Reporte semanal: falta 'date' o 'start_date'/'end_date'")
                    continue
                self.last_weekly_report_date = report_date or end_date
            elif report_type == "monthly":
                if start_date and end_date:
                    await self._generate_monthly_report_with_dates(start_date, end_date)
                elif report_date:
                    await self._generate_monthly_report(report_date)
                else:
                    logger.error("Reporte mensual: falta 'date' o 'start_date'/'end_date'")
                    continue
                self.last_monthly_report_date = report_date or end_date
    
    async def _generate_weekly_report(self, current_date: date):
        """Genera reporte semanal (usa current_date para calcular rango)"""
        logger.info("📊 Generando reporte semanal...")
        try:
            last_monday = current_date - timedelta(days=7)
            last_sunday = last_monday + timedelta(days=6)
            await self._generate_weekly_report_with_dates(last_monday, last_sunday)
        except Exception as e:
            logger.error(f"❌ Error generando reporte semanal: {e}", exc_info=True)
    
    async def _generate_weekly_report_with_dates(self, start_date: date, end_date: date):
        """Genera reporte semanal con rango de fechas dado"""
        try:
            rows = await self._fetch_appointment_rows(start_date, end_date)
            if self._precios_costs_cache is None:
                self._precios_costs_cache = await fetch_precios_extras_costs_dict(self.db)
            costs = self._precios_costs_cache
            summary = aggregate_financial_rows(rows, costs_dict=costs)
            daily_data = self._breakdown_by_day(rows, costs)
            marketing = await fetch_marketing_for_period(self.db, start_date, end_date)
            meta_analysis = await fetch_meta_analysis(
                self.db, start_date, end_date,
                total_ventas=summary["total_reservas_count"],
            )
            await self._send_weekly_report(
                start_date, end_date, summary, daily_data, marketing, meta_analysis
            )
        except Exception as e:
            logger.error(f"❌ Error generando reporte semanal: {e}", exc_info=True)
    
    async def _generate_monthly_report(self, current_date: date):
        """Genera reporte mensual (usa current_date para calcular rango)"""
        logger.info("📊 Generando reporte mensual...")
        try:
            first_day_current = current_date.replace(day=1)
            last_day_previous = first_day_current - timedelta(days=1)
            first_day_previous = last_day_previous.replace(day=1)
            await self._generate_monthly_report_with_dates(first_day_previous, last_day_previous)
        except Exception as e:
            logger.error(f"❌ Error generando reporte mensual: {e}", exc_info=True)
    
    async def _generate_monthly_report_with_dates(self, start_date: date, end_date: date):
        """Genera reporte mensual con rango de fechas dado"""
        try:
            rows = await self._fetch_appointment_rows(start_date, end_date)
            if self._precios_costs_cache is None:
                self._precios_costs_cache = await fetch_precios_extras_costs_dict(self.db)
            costs = self._precios_costs_cache
            summary = aggregate_financial_rows(rows, costs_dict=costs)
            daily_data = self._breakdown_by_day(rows, costs)
            weekly_data = self._breakdown_by_week(rows, costs)
            marketing = await fetch_marketing_for_period(self.db, start_date, end_date)
            await self._send_monthly_report(
                start_date, end_date, summary, daily_data, weekly_data, marketing
            )
        except Exception as e:
            logger.error(f"❌ Error generando reporte mensual: {e}", exc_info=True)
    
    async def _fetch_appointment_rows(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Mismas filas que el resumen diario: all_appointments + columnas para aggregate_financial_rows."""
        query = """
            SELECT 
                fecha,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                extras_json,
                costo_operativo_variable
            FROM all_appointments
            WHERE fecha BETWEEN %s AND %s AND status = 'confirmed'
        """
        return await self.db.execute_query(query, (start_date, end_date)) or []
    
    @staticmethod
    def _as_date(d: Any) -> Optional[date]:
        if d is None:
            return None
        if hasattr(d, "date") and not isinstance(d, date):
            return d.date()
        return d
    
    def _breakdown_by_day(self, rows: List[Dict[str, Any]], costs_dict: Dict[str, float]) -> List[Dict[str, Any]]:
        """Desglose diario con la misma agregación que el resumen (Precios Extras + extras_json)."""
        by_date: Dict[date, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            fe = self._as_date(r.get("fecha"))
            if fe is not None:
                by_date[fe].append(r)
        out: List[Dict[str, Any]] = []
        for fe in sorted(by_date.keys()):
            agg = aggregate_financial_rows(by_date[fe], costs_dict=costs_dict)
            out.append({
                "fecha": fe,
                "num_reservas": agg["total_reservas_count"],
                "ingresos": agg["total_ingresos"],
                "costo_variable_extras": agg["total_costo_variable_extras"],
                "costo_variable_aloj": agg["total_costo_variable_aloj"],
            })
        return out
    
    def _breakdown_by_week(self, rows: List[Dict[str, Any]], costs_dict: Dict[str, float]) -> List[Dict[str, Any]]:
        """Desglose por semana (lunes inicio), misma agregación que el resumen."""
        by_week: Dict[date, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            d = self._as_date(r.get("fecha"))
            if d is None:
                continue
            week_start = d - timedelta(days=d.weekday())
            by_week[week_start].append(r)
        out: List[Dict[str, Any]] = []
        for ws in sorted(by_week.keys()):
            agg = aggregate_financial_rows(by_week[ws], costs_dict=costs_dict)
            out.append({
                "semana": ws,
                "num_reservas": agg["total_reservas_count"],
                "ingresos": agg["total_ingresos"],
                "costo_variable_extras": agg["total_costo_variable_extras"],
                "costo_variable_aloj": agg["total_costo_variable_aloj"],
            })
        return out
    
    async def _send_weekly_report(
        self,
        start_date: date,
        end_date: date,
        summary: Dict[str, Any],
        daily_data: List[Dict[str, Any]],
        marketing: Dict[str, Any],
        meta_analysis: str = "",
    ):
        """Envía reporte semanal por email"""
        
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")
        num_dias = (end_date - start_date).days + 1
        fijo_periodo = self.costo_fijo_diario_prorrateado * num_dias
        n_res = summary['total_reservas_count']
        cop_fijo_reservas = self.costo_operativo_fijo_por_reserva * n_res
        total_marketing = float(marketing.get("total_marketing") or 0)
        num_ads_mkt = int(marketing.get("num_ads") or 0)
        total_costos = (
            fijo_periodo
            + cop_fijo_reservas
            + total_marketing
            + summary['total_costo_variable_extras']
            + summary['total_costo_variable_aloj']
        )
        utilidad = summary['total_ingresos'] - total_costos
        margen = (utilidad / summary['total_ingresos'] * 100) if summary['total_ingresos'] > 0 else 0
        
        message = f"""
📅 REPORTE SEMANAL - {start_str} al {end_str}

{'='*40}
📊 RESUMEN GENERAL

📅 Citas confirmadas: {summary['total_reservas_count']}
🗓️ Días con reservas: {summary['dias_con_reservas']}/{num_dias}

{'='*40}
💰 INGRESOS

💵 Total reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Total extras: ${summary['total_ingreso_extras']:,.0f}
🏠 Total alojamientos: ${summary['total_ingreso_aloj']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${summary['total_ingresos']:,.0f}

📊 Promedio/reserva: ${summary['promedio_por_reserva']:,.0f}

{'='*40}
💸 COSTOS Y UTILIDAD

🏭 Costo fijo prorrateado ({num_dias} días × ${self.costo_fijo_diario_prorrateado:,.0f}): ${fijo_periodo:,.0f}
🏭 Costos operativos fijos ({n_res} reservas × ${self.costo_operativo_fijo_por_reserva:,.0f}): ${cop_fijo_reservas:,.0f}
📢 Marketing: ${total_marketing:,.0f} ({num_ads_mkt} anuncios)
   Variables — extras: ${summary['total_costo_variable_extras']:,.0f}
   Variables — alojamientos: ${summary['total_costo_variable_aloj']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: ${total_costos:,.0f}
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

        # Bloque de analisis Meta Ads (hallazgos + recomendaciones)
        if meta_analysis:
            message += f"\n{meta_analysis}\n"

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
        weekly_data: List[Dict[str, Any]],
        marketing: Dict[str, Any],
    ):
        """Envía reporte mensual por email"""
        
        mes_nombre = calendar.month_name[start_date.month]
        year = start_date.year
        
        num_dias = (end_date - start_date).days + 1
        fijo_periodo = self.costo_fijo_diario_prorrateado * num_dias
        n_res = summary['total_reservas_count']
        cop_fijo_reservas = self.costo_operativo_fijo_por_reserva * n_res
        total_marketing = float(marketing.get("total_marketing") or 0)
        num_ads_mkt = int(marketing.get("num_ads") or 0)
        total_costos = (
            fijo_periodo
            + cop_fijo_reservas
            + total_marketing
            + summary['total_costo_variable_extras']
            + summary['total_costo_variable_aloj']
        )
        utilidad = summary['total_ingresos'] - total_costos
        margen = (utilidad / summary['total_ingresos'] * 100) if summary['total_ingresos'] > 0 else 0
        
        promedio_dia = summary['total_ingresos'] / num_dias if num_dias > 0 else 0
        
        message = f"""
📅 REPORTE MENSUAL - {mes_nombre} {year}

{'='*40}
📊 RESUMEN GENERAL

📅 Citas confirmadas: {summary['total_reservas_count']}
🗓️ Días con reservas: {summary['dias_con_reservas']}/{num_dias}

{'='*40}
💰 INGRESOS

💵 Total reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Total extras: ${summary['total_ingreso_extras']:,.0f}
🏠 Total alojamientos: ${summary['total_ingreso_aloj']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${summary['total_ingresos']:,.0f}

📊 Promedio/reserva: ${summary['promedio_por_reserva']:,.0f}
📅 Promedio/día: ${promedio_dia:,.0f}

{'='*40}
💸 COSTOS Y UTILIDAD

🏭 Costo fijo prorrateado ({num_dias} días × ${self.costo_fijo_diario_prorrateado:,.0f}): ${fijo_periodo:,.0f}
🏭 Costos operativos fijos ({n_res} reservas × ${self.costo_operativo_fijo_por_reserva:,.0f}): ${cop_fijo_reservas:,.0f}
📢 Marketing: ${total_marketing:,.0f} ({num_ads_mkt} anuncios)
   Variables — extras: ${summary['total_costo_variable_extras']:,.0f}
   Variables — alojamientos: ${summary['total_costo_variable_aloj']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: ${total_costos:,.0f}
💵 UTILIDAD: ${utilidad:,.0f}
📊 Margen: {margen:.1f}%

{'='*40}
📈 DESGLOSE SEMANAL

"""
        
        # Agregar datos semanales
        for idx, week_data in enumerate(weekly_data, 1):
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
