"""
Monitor de Resumen Semanal y Mensual
Envía reportes los lunes a las 9:00 AM con información de la semana o el mes
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, time as dt_time, date
import asyncio
import pytz
import calendar
from pathlib import Path
import tempfile

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    mdates = None

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class WeeklyMonthlySummaryMonitor(BaseMonitor):
    """Envía resumen semanal los lunes y mensual el primer lunes del mes"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        # Chequear cada 5 minutos si es hora de enviar el reporte
        self.check_interval = config.get("check_interval", 300)
        # Hora para enviar el reporte (por defecto 9:00 AM)
        report_time = config.get("report_time", "09:00")
        hour, minute = map(int, report_time.split(":"))
        self.report_time = dt_time(hour, minute)
        # Flag para saber si ya se envió esta semana/mes
        self.last_weekly_report_date = None
        self.last_monthly_report_date = None
        # Zona horaria
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
        """Verifica si es lunes y hora de enviar el reporte"""
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)
        current_time = now_local.time()
        current_date = now_local.date()
        
        # Verificar si es lunes (weekday() == 0)
        if now_local.weekday() != 0:
            return []
        
        # Verificar si ya pasó la hora de reporte
        if not self._has_passed_report_time(current_time):
            return []
        
        # Determinar si es el primer lunes del mes
        is_first_monday = self._is_first_monday_of_month(current_date)
        
        reports_to_generate = []
        
        # Reporte mensual (primer lunes del mes)
        if is_first_monday and self.last_monthly_report_date != current_date:
            logger.info(f"📅 Es el primer lunes del mes - Generando reporte mensual")
            self.last_monthly_report_date = current_date
            # Calcular mes anterior
            first_day_current_month = current_date.replace(day=1)
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            first_day_previous_month = last_day_previous_month.replace(day=1)
            
            reports_to_generate.append({
                "type": "monthly",
                "start_date": first_day_previous_month,
                "end_date": last_day_previous_month
            })
        
        # Reporte semanal (todos los lunes)
        if self.last_weekly_report_date != current_date:
            logger.info(f"📅 Es lunes - Generando reporte semanal")
            self.last_weekly_report_date = current_date
            # Calcular semana anterior (lunes a domingo)
            # Si hoy es lunes, la semana anterior termina el domingo pasado
            last_sunday = current_date - timedelta(days=1)
            last_monday = last_sunday - timedelta(days=6)
            
            reports_to_generate.append({
                "type": "weekly",
                "start_date": last_monday,
                "end_date": last_sunday
            })
        
        return reports_to_generate
    
    def _has_passed_report_time(self, current_time: dt_time) -> bool:
        """Determina si ya se alcanzó la hora de reporte configurada
        
        Considera una ventana de 30 minutos después de la hora configurada
        para asegurar que el reporte se envíe aunque el sistema no esté
        corriendo exactamente a la hora programada.
        """
        # Convertir a minutos desde medianoche para comparar
        current_minutes = current_time.hour * 60 + current_time.minute
        report_minutes = self.report_time.hour * 60 + self.report_time.minute
        
        # Ventana de 30 minutos: si estamos entre report_time y report_time + 30min
        if current_minutes >= report_minutes and current_minutes < report_minutes + 30:
            return True
        
        return False
    
    def _is_first_monday_of_month(self, date_to_check: date) -> bool:
        """Determina si la fecha es el primer lunes del mes"""
        # Verificar que sea lunes
        if date_to_check.weekday() != 0:
            return False
        
        # Verificar que esté en la primera semana del mes (día <= 7)
        if date_to_check.day <= 7:
            return True
        
        return False
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """Genera y envía los reportes semanales/mensuales"""
        if not current_state:
            return
        
        # Importar el monitor diario para reutilizar sus métodos
        from app.monitors.daily_summary_monitor import DailySummaryMonitor
        daily_monitor_config = self.config  # Usar la misma config
        daily_monitor = DailySummaryMonitor(
            self.settings,
            daily_monitor_config,
            self.notification_manager
        )
        daily_monitor.db = self.db  # Reutilizar la conexión
        
        for report_config in current_state:
            report_type = report_config.get("type")
            start_date = report_config.get("start_date")
            end_date = report_config.get("end_date")
            
            try:
                logger.info(f"📊 Generando reporte {report_type} desde {start_date} hasta {end_date}")
                
                # Agregar datos de todos los días en el rango
                total_appointments = 0
                total_info_completed = 0
                all_missing_details = []
                total_revenue = 0
                total_revenue_reservations = 0
                total_revenue_extras = 0
                total_marketing_cost = 0
                total_operational_cost = 0
                total_operational_profit = 0
                total_costs = 0
                total_net_profit = 0
                daily_revenues = []
                
                current_date = start_date
                while current_date <= end_date:
                    # Contar reservas y información completada
                    day_appointments = await daily_monitor._count_appointments(current_date)
                    day_info = await daily_monitor._count_info_reservas(current_date)
                    
                    total_appointments += day_appointments
                    total_info_completed += day_info
                    
                    # Calcular ingresos del día
                    day_revenue = await daily_monitor._calculate_revenue_for_date(current_date)
                    
                    if day_revenue.get('total_reservations', 0) > 0:
                        daily_revenues.append({
                            'date': current_date,
                            'revenue_data': day_revenue
                        })
                        
                        total_revenue += day_revenue.get('total_revenue', 0)
                        total_revenue_reservations += day_revenue.get('revenue_reservations', 0)
                        total_revenue_extras += day_revenue.get('revenue_extras', 0)
                        total_marketing_cost += day_revenue.get('marketing_cost', 0)
                        operational_costs = day_revenue.get('operational_costs', {})
                        total_operational_cost += operational_costs.get('total', 0)
                        total_operational_profit += day_revenue.get('operational_profit', 0)
                        total_costs += day_revenue.get('total_costs', 0)
                        total_net_profit += day_revenue.get('net_profit', 0)
                    
                    current_date += timedelta(days=1)
                
                # Calcular promedio diario
                num_days = (end_date - start_date).days + 1
                avg_daily_revenue = total_revenue / num_days if num_days > 0 else 0
                avg_revenue_per_reservation = total_revenue / total_appointments if total_appointments > 0 else 0
                
                # Generar gráficos
                chart_path = None
                if MATPLOTLIB_AVAILABLE:
                    try:
                        if report_type == "weekly":
                            chart_path = await self._generate_weekly_chart(
                                start_date,
                                end_date,
                                total_revenue,
                                daily_monitor
                            )
                        elif report_type == "monthly":
                            chart_path = await self._generate_monthly_chart(
                                start_date,
                                end_date,
                                total_revenue,
                                daily_monitor
                            )
                    except Exception as chart_error:
                        logger.error(f"❌ Error generando gráfico: {chart_error}")
                
                # Construir y enviar reporte
                await self._send_period_report(
                    report_type,
                    start_date,
                    end_date,
                    total_appointments,
                    total_info_completed,
                    total_revenue,
                    total_revenue_reservations,
                    total_revenue_extras,
                    total_marketing_cost,
                    total_operational_cost,
                    total_operational_profit,
                    total_costs,
                    total_net_profit,
                    avg_daily_revenue,
                    avg_revenue_per_reservation,
                    daily_revenues,
                    chart_path
                )
                
            except Exception as e:
                logger.error(f"❌ Error generando reporte {report_type}: {e}", exc_info=True)
    
    async def _get_weekly_revenue_history(self, end_date: date, weeks_back: int, daily_monitor) -> List[Dict]:
        """Obtiene el historial de ingresos semanales hacia atrás"""
        weekly_data = []
        
        current_week_end = end_date
        
        for week_num in range(weeks_back):
            # Calcular lunes y domingo de esta semana
            week_monday = current_week_end - timedelta(days=current_week_end.weekday() + 7 * week_num)
            week_sunday = week_monday + timedelta(days=6)
            
            # Calcular ingresos de la semana
            week_total = 0
            current_date = week_monday
            
            while current_date <= week_sunday:
                day_revenue = await daily_monitor._calculate_revenue_for_date(current_date)
                week_total += day_revenue.get('total_revenue', 0)
                current_date += timedelta(days=1)
            
            weekly_data.append({
                'week_start': week_monday,
                'week_end': week_sunday,
                'total_revenue': week_total
            })
        
        return list(reversed(weekly_data))  # Más antiguo primero
    
    async def _generate_weekly_chart(
        self,
        current_week_start: date,
        current_week_end: date,
        current_week_revenue: float,
        daily_monitor
    ) -> Optional[str]:
        """Genera un gráfico de evolución de ingresos semanales"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("⚠️ Matplotlib no disponible, no se puede generar gráfico")
            return None
        
        try:
            # Obtener últimos 3 meses (aprox 12 semanas)
            logger.info("📊 Generando gráfico de evolución semanal...")
            weeks_history = await self._get_weekly_revenue_history(current_week_end, 12, daily_monitor)
            
            # Obtener datos del año anterior (misma semana o la más cercana)
            last_year_week_start = current_week_start - timedelta(days=365)
            last_year_week_end = current_week_end - timedelta(days=365)
            
            # Calcular ingresos del año anterior
            last_year_total = 0
            current_date = last_year_week_start
            while current_date <= last_year_week_end:
                day_revenue = await daily_monitor._calculate_revenue_for_date(current_date)
                last_year_total += day_revenue.get('total_revenue', 0)
                current_date += timedelta(days=1)
            
            # Preparar datos para el gráfico
            week_labels = []
            revenues = []
            
            for week_data in weeks_history:
                week_start = week_data['week_start']
                label = week_start.strftime("%d/%m")
                week_labels.append(label)
                revenues.append(week_data['total_revenue'] / 1_000_000)  # Convertir a millones
            
            # Crear el gráfico
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Gráfico de líneas
            ax.plot(week_labels, revenues, marker='o', linewidth=2, markersize=8, 
                   color='#0dcaf0', label='Ingresos Semanales')
            
            # Agregar línea horizontal para el promedio de los últimos 3 meses
            avg_revenue = sum(revenues) / len(revenues) if revenues else 0
            ax.axhline(y=avg_revenue, color='gray', linestyle='--', alpha=0.5, 
                      label=f'Promedio últimos 3 meses: ${avg_revenue:.2f}M')
            
            # Agregar referencia del año anterior
            if last_year_total > 0:
                last_year_millions = last_year_total / 1_000_000
                ax.axhline(y=last_year_millions, color='orange', linestyle='-.', alpha=0.7,
                          label=f'Mismo período año anterior: ${last_year_millions:.2f}M')
            
            # Configuración del gráfico
            ax.set_xlabel('Semana (inicio)', fontsize=11)
            ax.set_ylabel('Ingresos (Millones CLP)', fontsize=11)
            
            # Título con información del período
            first_week = weeks_history[0]['week_start'].strftime("%d/%m")
            last_week = weeks_history[-1]['week_end'].strftime("%d/%m/%Y")
            ax.set_title(f'Evolución de Ingresos Semanales\n{first_week} - {last_week} (Últimos 3 meses)', 
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=10)
            
            # Rotar etiquetas del eje x
            plt.xticks(rotation=45, ha='right')
            
            # Ajustar layout
            plt.tight_layout()
            
            # Guardar en archivo temporal
            temp_dir = Path(tempfile.gettempdir())
            chart_filename = f"hotboat_weekly_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = temp_dir / chart_filename
            
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Gráfico semanal generado: {chart_path}")
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"❌ Error generando gráfico semanal: {e}", exc_info=True)
            return None
    
    async def _get_monthly_revenue_history(self, end_date: date, daily_monitor) -> List[Dict]:
        """Obtiene el historial de ingresos mensuales del año actual"""
        monthly_data = []
        
        # Obtener todos los meses del año hasta el mes del end_date
        current_year = end_date.year
        end_month = end_date.month
        
        for month_num in range(1, end_month + 1):
            # Primer y último día del mes
            month_start = date(current_year, month_num, 1)
            
            # Último día del mes
            if month_num == 12:
                month_end = date(current_year, 12, 31)
            else:
                next_month = date(current_year, month_num + 1, 1)
                month_end = next_month - timedelta(days=1)
            
            # Si estamos en el mes actual, usar end_date como límite
            if month_num == end_month:
                month_end = min(month_end, end_date)
            
            # Calcular ingresos del mes
            month_total = 0
            current_date = month_start
            
            while current_date <= month_end:
                day_revenue = await daily_monitor._calculate_revenue_for_date(current_date)
                month_total += day_revenue.get('total_revenue', 0)
                current_date += timedelta(days=1)
            
            monthly_data.append({
                'month': month_num,
                'month_name': month_start.strftime("%B"),
                'month_short': month_start.strftime("%b"),
                'year': current_year,
                'total_revenue': month_total
            })
        
        return monthly_data
    
    async def _generate_monthly_chart(
        self,
        current_month_start: date,
        current_month_end: date,
        current_month_revenue: float,
        daily_monitor
    ) -> Optional[str]:
        """Genera un gráfico de evolución de ingresos mensuales del año"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("⚠️ Matplotlib no disponible, no se puede generar gráfico")
            return None
        
        try:
            # Obtener datos de todos los meses del año actual
            logger.info("📊 Generando gráfico de evolución mensual...")
            months_history = await self._get_monthly_revenue_history(current_month_end, daily_monitor)
            
            # Obtener datos del año anterior (mismo mes)
            last_year_month_start = date(current_month_start.year - 1, current_month_start.month, 1)
            
            # Último día del mes del año anterior
            if current_month_start.month == 12:
                last_year_month_end = date(current_month_start.year - 1, 12, 31)
            else:
                next_month = date(current_month_start.year - 1, current_month_start.month + 1, 1)
                last_year_month_end = next_month - timedelta(days=1)
            
            # Calcular ingresos del mismo mes del año anterior
            last_year_total = 0
            current_date = last_year_month_start
            while current_date <= last_year_month_end:
                day_revenue = await daily_monitor._calculate_revenue_for_date(current_date)
                last_year_total += day_revenue.get('total_revenue', 0)
                current_date += timedelta(days=1)
            
            # Preparar datos para el gráfico
            month_labels = []
            revenues = []
            
            for month_data in months_history:
                month_labels.append(month_data['month_short'])
                revenues.append(month_data['total_revenue'] / 1_000_000)  # Convertir a millones
            
            # Crear el gráfico
            fig, ax = plt.subplots(figsize=(14, 7))
            
            # Gráfico de barras
            bars = ax.bar(month_labels, revenues, color='#0dcaf0', alpha=0.8, label='Ingresos Mensuales')
            
            # Agregar valores sobre las barras
            for i, (bar, revenue) in enumerate(zip(bars, revenues)):
                if revenue > 0:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'${revenue:.1f}M',
                           ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            # Agregar línea horizontal para el promedio del año
            avg_revenue = sum(revenues) / len(revenues) if revenues else 0
            ax.axhline(y=avg_revenue, color='gray', linestyle='--', alpha=0.5, 
                      label=f'Promedio del año: ${avg_revenue:.2f}M')
            
            # Agregar referencia del mismo mes del año anterior
            if last_year_total > 0:
                last_year_millions = last_year_total / 1_000_000
                current_month_name = current_month_start.strftime("%B")
                ax.axhline(y=last_year_millions, color='orange', linestyle='-.', alpha=0.7,
                          label=f'{current_month_name} {current_month_start.year - 1}: ${last_year_millions:.2f}M')
            
            # Configuración del gráfico
            ax.set_xlabel('Mes', fontsize=12)
            ax.set_ylabel('Ingresos (Millones CLP)', fontsize=12)
            
            # Título con información del año
            current_year = current_month_end.year
            ax.set_title(f'Evolución de Ingresos Mensuales - Año {current_year}', 
                        fontsize=15, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            ax.legend(loc='best', fontsize=10)
            
            # Ajustar layout
            plt.tight_layout()
            
            # Guardar en archivo temporal
            temp_dir = Path(tempfile.gettempdir())
            chart_filename = f"hotboat_monthly_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = temp_dir / chart_filename
            
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Gráfico mensual generado: {chart_path}")
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"❌ Error generando gráfico mensual: {e}", exc_info=True)
            return None
    
    async def _send_period_report(
        self,
        report_type: str,
        start_date: date,
        end_date: date,
        total_appointments: int,
        total_info_completed: int,
        total_revenue: float,
        revenue_reservations: float,
        revenue_extras: float,
        total_marketing_cost: float,
        total_operational_cost: float,
        total_operational_profit: float,
        total_costs: float,
        total_net_profit: float,
        avg_daily_revenue: float,
        avg_revenue_per_reservation: float,
        daily_revenues: List[Dict[str, Any]],
        chart_path: Optional[str] = None
    ) -> None:
        """Envía el reporte semanal o mensual por Email"""
        
        period_name = "SEMANAL" if report_type == "weekly" else "MENSUAL"
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")
        
        num_days = (end_date - start_date).days + 1
        net_margin = (total_net_profit / total_revenue * 100) if total_revenue > 0 else 0
        avg_daily_marketing_cost = total_marketing_cost / num_days if num_days > 0 else 0
        avg_daily_operational_cost = total_operational_cost / num_days if num_days > 0 else 0
        avg_daily_net_profit = total_net_profit / num_days if num_days > 0 else 0
        
        # Construir mensaje
        message = f"""
{'🗓️' if report_type == 'weekly' else '📆'} REPORTE {period_name}
Período: {start_str} - {end_str} ({num_days} días)

{"="*40}
📊 RESUMEN DE OPERACIONES

📅 Total Reservas: {total_appointments}
📝 Información Completada: {total_info_completed}
📋 Tasa de Completitud: {(total_info_completed / total_appointments * 100) if total_appointments > 0 else 0:.1f}%

{"="*40}
💰 RESUMEN DE INGRESOS

💵 Total Reservas: ${revenue_reservations:,.0f}
🍾 Total Extras: ${revenue_extras:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${total_revenue:,.0f}

📊 Promedio Diario: ${avg_daily_revenue:,.0f}
📈 Promedio por Reserva: ${avg_revenue_per_reservation:,.0f}

{"="*40}
💸 RESUMEN DE COSTOS

📢 Marketing: ${total_marketing_cost:,.0f} (${avg_daily_marketing_cost:,.0f}/día)
🏭 Operativos: ${total_operational_cost:,.0f} (${avg_daily_operational_cost:,.0f}/día)
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: ${total_costs:,.0f}

{"="*40}
📈 UTILIDAD NETA

💰 Ingresos: ${total_revenue:,.0f}
💸 Costos Totales: -${total_costs:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD NETA: ${total_net_profit:,.0f}
📊 Margen Neto: {net_margin:.1f}%

📊 Utilidad Promedio Diaria: ${avg_daily_net_profit:,.0f}

{"="*40}
📅 DETALLE POR DÍA

"""
        
        # Agregar detalle de días con actividad
        days_with_activity = [d for d in daily_revenues if d['revenue_data'].get('total_revenue', 0) > 0]
        
        for day_data in days_with_activity[:14]:  # Limitar a 14 días para no hacer el email muy largo
            day_date = day_data['date']
            revenue_data = day_data['revenue_data']
            
            day_str = day_date.strftime("%d/%m")
            weekday_name = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][day_date.weekday()]
            
            day_total = revenue_data.get('total_revenue', 0)
            day_reservations = revenue_data.get('revenue_reservations', 0)
            day_extras = revenue_data.get('revenue_extras', 0)
            day_count = revenue_data.get('total_reservations', 0)
            day_marketing = revenue_data.get('marketing_cost', 0)
            day_operational_costs = revenue_data.get('operational_costs', {}).get('total', 0)
            day_net_profit = revenue_data.get('net_profit', 0)
            
            message += f"{weekday_name} {day_str}: ${day_total:,.0f} | "
            message += f"Costos: ${day_marketing + day_operational_costs:,.0f} | "
            message += f"Utilidad Neta: ${day_net_profit:,.0f}\n"
            message += f"  ({day_count} reservas, Marketing: ${day_marketing:,.0f}, Operativos: ${day_operational_costs:,.0f})\n"
        
        if len(daily_revenues) > 14:
            message += f"\n... y {len(daily_revenues) - 14} días más.\n"
        
        # Top 5 días con más ingresos
        if daily_revenues:
            message += f"\n{'='*40}\n"
            message += "🏆 TOP 5 DÍAS CON MEJORES INGRESOS\n\n"
            
            sorted_days = sorted(
                daily_revenues,
                key=lambda x: x['revenue_data'].get('total_revenue', 0),
                reverse=True
            )[:5]
            
            for idx, day_data in enumerate(sorted_days, 1):
                day_date = day_data['date']
                revenue_data = day_data['revenue_data']
                
                day_str = day_date.strftime("%d/%m/%Y")
                day_total = revenue_data.get('total_revenue', 0)
                day_count = revenue_data.get('total_reservations', 0)
                
                message += f"{idx}. {day_str}: ${day_total:,.0f} ({day_count} reservas)\n"
        
        message += f"\n{'='*40}\n"
        
        # Mencionar gráfico si está disponible
        if chart_path:
            message += "📊 Ver gráfico de evolución adjunto\n\n"
        
        message += f"📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}\n"
        
        # Preparar adjuntos
        attachments = None
        if chart_path and Path(chart_path).exists():
            filename_prefix = 'semanal' if report_type == 'weekly' else 'mensual'
            attachments = [{
                'path': chart_path,
                'filename': f'evolucion_ingresos_{filename_prefix}_{start_date.strftime("%Y%m%d")}.png',
                'content_type': 'image/png'
            }]
        
        # Enviar por Email
        try:
            sent = await self.send_notification(
                message=message,
                priority="high",
                channel="email",
                attachments=attachments
            )
            if sent:
                logger.info(f"✅ Reporte {period_name} enviado por Email")
            else:
                logger.error(f"❌ No se pudo enviar el reporte {period_name}")
            
            # Limpiar archivo temporal del gráfico
            if chart_path and Path(chart_path).exists():
                try:
                    Path(chart_path).unlink()
                    logger.debug(f"🗑️ Gráfico temporal eliminado: {chart_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ No se pudo eliminar gráfico temporal: {cleanup_error}")
                    
        except Exception as e:
            logger.error(f"❌ Error enviando reporte {period_name}: {e}")
