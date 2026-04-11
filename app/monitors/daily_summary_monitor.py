"""
Monitor de Resumen Diario - Versión Simplificada
Lee de la tabla all_appointments (solo status = confirmed).
Desglose extras vs alojamiento por claves aloj* en extras_json.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, time as dt_time
import pytz

from app.monitors.base_monitor import BaseMonitor
from app.monitors.extras_json_split import (
    aggregate_financial_rows,
    split_row_extras_income,
)
from app.utils.extras_pricing import fetch_precios_extras_costs_dict
from app.utils.marketing_costs import fetch_marketing_for_date
from app.logger import logger


class DailySummaryMonitor(BaseMonitor):
    """Envía resumen diario leyendo de all_appointments"""
    
    # Ver BaseMonitor.start: permitir enviar en la primera iteración si ya es hora de reporte
    process_first_cycle_when_state_nonempty = True
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 300)
        report_time = config.get("report_time", "09:00")
        hour, minute = map(int, report_time.split(":"))
        self.report_time = dt_time(hour, minute)
        self.last_report_date = None
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
            # Misma base que semanal/mensual: recargar costos desde "Precios Extras" en cada envío
            self._precios_costs_cache = None
            yesterday = self._yesterday_in_report_timezone()
            
            summary_data = await self._get_daily_summary(yesterday)
            marketing_cost = await fetch_marketing_for_date(self.db, yesterday)
            
            await self._send_daily_report(yesterday, summary_data, marketing_cost)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte diario: {e}", exc_info=True)
    
    async def _get_daily_summary(self, date) -> Dict[str, Any]:
        """Agrega ingresos y costos variables (extras vs aloj) desde all_appointments."""
        query = """
            SELECT 
                fecha,
                ingreso_reserva,
                ingreso_extras,
                ingreso_total,
                extras_json,
                costo_operativo_variable
            FROM all_appointments
            WHERE fecha = %s AND status = 'confirmed'
        """
        
        rows = await self.db.execute_query(query, (date,)) or []
        if self._precios_costs_cache is None:
            self._precios_costs_cache = await fetch_precios_extras_costs_dict(self.db)
        return aggregate_financial_rows(rows, costs_dict=self._precios_costs_cache)
    
    async def _get_marketing_cost(self, date) -> Dict[str, Any]:
        """Costos de marketing del día (vista marketing_costs_daily). Scripts legacy."""
        return await fetch_marketing_for_date(self.db, date)
    
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
                extras_json
            FROM all_appointments
            WHERE fecha = %s AND status = 'confirmed'
            ORDER BY hora
            LIMIT %s
        """
        
        try:
            rows = await self.db.execute_query(query, (date, limit))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo detalle de reservas: {e}")
            return []
    
    async def _send_daily_report(
        self, 
        date, 
        summary: Dict[str, Any],
        marketing: Dict[str, Any]
    ) -> None:
        """Envía el reporte diario por Email"""
        
        date_str = date.strftime("%d/%m/%Y")
        
        total_reservas = summary['total_reservas_count']
        total_ingresos = summary['total_ingresos']
        
        fijo = self.costo_fijo_diario_prorrateado
        cop_fijo_reservas = self.costo_operativo_fijo_por_reserva * total_reservas
        total_marketing = marketing['total_marketing']
        cv_extras = summary['total_costo_variable_extras']
        cv_aloj = summary['total_costo_variable_aloj']
        
        total_costos = fijo + cop_fijo_reservas + total_marketing + cv_extras + cv_aloj
        utilidad_neta = total_ingresos - total_costos
        margen_neto = (utilidad_neta / total_ingresos * 100) if total_ingresos > 0 else 0
        
        message = f"""
📊 REPORTE DIARIO - {date_str}

📅 Reservas del día: {total_reservas}

{'='*40}
💰 INGRESOS DEL DÍA

💵 Total reservas: ${summary['total_ingreso_reservas']:,.0f}
🍾 Total extras: ${summary['total_ingreso_extras']:,.0f}
🏠 Total alojamientos: ${summary['total_ingreso_aloj']:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${total_ingresos:,.0f}

📊 Promedio por reserva: ${summary['promedio_por_reserva']:,.0f}
🧾 Pagos registrados: {total_reservas}

{'='*40}
💸 COSTOS DEL DÍA

📢 Marketing: ${total_marketing:,.0f} ({marketing['num_ads']} anuncios)

🏭 Costo fijo diario prorrateado: ${fijo:,.0f}

🏭 Costos operativos fijos ({total_reservas} reservas × ${self.costo_operativo_fijo_por_reserva:,.0f}): ${cop_fijo_reservas:,.0f}

   Variables — extras: ${cv_extras:,.0f}
   Variables — alojamientos: ${cv_aloj:,.0f}
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
        
        detalle = await self._get_reservas_detalle(date)
        if detalle:
            message += f"\n{'='*40}\n"
            message += "DETALLE POR RESERVA:\n\n"
            
            for idx, res in enumerate(detalle, 1):
                time_str = res['hora'].strftime("%H:%M") if res['hora'] else "N/A"
                message += f"{idx}. {time_str} - {res['nombre_cliente'] or 'Sin nombre'}\n"
                
                if res['num_personas']:
                    message += f"   👥 {res['num_personas']} personas\n"
                
                message += f"   💵 Subtotal reserva: ${float(res['ingreso_reserva'] or 0):,.0f}\n"
                
                ie = float(res['ingreso_extras'] or 0)
                e_inc, a_inc = split_row_extras_income(res.get('extras_json'), ie)
                if ie > 0 or e_inc > 0 or a_inc > 0:
                    message += f"   🍾 Extras: ${e_inc:,.0f}\n"
                    message += f"   🏠 Alojamientos: ${a_inc:,.0f}\n"
                    if res.get('extras_json') and isinstance(res['extras_json'], dict):
                        lineas = []
                        for k, v in list(res['extras_json'].items())[:5]:
                            pref = "🏠" if str(k).lower().startswith("aloj") else "•"
                            lineas.append(f"{pref} {k}")
                        if lineas:
                            message += f"      ({', '.join(lineas)})\n"
                
                message += f"   💰 Total: ${float(res['ingreso_total'] or 0):,.0f}\n\n"
            
            if total_reservas > len(detalle):
                message += f"... y {total_reservas - len(detalle)} reservas más.\n\n"
        
        message += f"\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
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
