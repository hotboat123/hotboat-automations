""" 
Monitor de Resumen Diario 
Envía un reporte cada mañana comparando reservas vs información completada 
""" 
from typing import Dict, Any, List, Optional 
from datetime import datetime, timedelta, time as dt_time 
from decimal import Decimal
import asyncio 
import json 
import re 
import pytz 

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
        # Zona horaria (por defecto Chile) 
        timezone_str = config.get("timezone", "America/Santiago") 
        try: 
            self.timezone = pytz.timezone(timezone_str) 
        except: 
            self.timezone = pytz.UTC 
            logger.warning(f"⚠️  Zona horaria '{timezone_str}' no válida, usando UTC") 
        # Tolerancia de coincidencia para cruzar reservas vs información (en minutos) 
        self.match_tolerance_minutes = config.get("match_tolerance_minutes", 15) 
        self.match_tolerance_seconds = max(0, self.match_tolerance_minutes) * 60 
        # Listas de posibles claves en el formulario 
        self.form_date_keys = [ 
            "fecha", 
            "fecha_reserva", 
            "fecha de reserva", 
            "fecha_salida", 
            "fecha de salida", 
            "fecha salida", 
            "fecha del servicio", 
            "fecha_servicio", 
            "fecha salida reserva", 
            "fecha de salida reserva", 
            "dia", 
            "día" 
        ] 
        self.form_time_keys = [ 
            "hora_salida", 
            "hora salida", 
            "hora de salida", 
            "hora_salida_reserva", 
            "hora salida reserva", 
            "horario_salida", 
            "horario salida", 
            "horario de salida", 
            "hora", 
            "horario", 
            "hora de reserva", 
            "hora_reserva", 
            "hora salida 1", 
            "hora salida 2" 
        ] 
        self.consumption_prefixes = (
            "extras",
            "cervezas",
            "tablas",
            "bebidas_y_jugos",
            "otros_alcoholes",
            "cha",
            "bebidas",
            "jugos"
        )
    
    async def initialize(self):
        """Inicializa el monitor"""
        await super().initialize()
        logger.info(f"📊 Monitor de Resumen Diario inicializado (envío: {self.report_time.strftime('%H:%M')})")
    
    async def check(self) -> List[Dict[str, Any]]:
        """
        Verifica si es hora de enviar el reporte diario
        """
        # Obtener hora actual en la zona horaria configurada
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)
        current_time = now_local.time()
        current_date = now_local.date()
        
        # Verificar si es hora de enviar y no se ha enviado hoy
        if (self._has_passed_report_time(current_time) and
                self.last_report_date != current_date):
            
            logger.info(f"⏰ Es hora de enviar el reporte diario ({current_time.strftime('%H:%M')} {self.timezone})")
            
            # Marcar como enviado hoy
            self.last_report_date = current_date
            
            # Retornar datos para generar el reporte
            return [{"generate_report": True, "date": current_date}]
        
        return []

    def _has_passed_report_time(self, current_time: dt_time) -> bool:
        """Determina si ya se alcanzó la hora de reporte configurada."""
        if current_time.hour > self.report_time.hour:
            return True
        if current_time.hour == self.report_time.hour and current_time.minute >= self.report_time.minute:
            return True
        return False
    
    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        """
        Genera y envía el reporte diario
        """
        if not current_state:
            return
        
        if not current_state[0].get("generate_report"):
            return
        
        logger.info("📊 Generando reporte diario...")
        
        try:
            # Obtener datos de ayer
            yesterday = datetime.now().date() - timedelta(days=1)
            
            # Contar reservas de ayer en appointments
            appointments_count = await self._count_appointments(yesterday)
            
            # Contar información completada de ayer
            info_reservas_count = await self._count_info_reservas(yesterday)
            
            # Obtener detalle de información completada
            info_details = await self._get_info_reservas_details(yesterday)
            consumption_summary = await self._get_consumption_summary(
                [entry.get("info_id") for entry in (info_details or []) if entry.get("info_id")]
            )
            
            # Obtener detalles de reservas sin información
            missing_details = await self._get_missing_reservas(yesterday, info_details)
            
            # Generar y enviar el mensaje
            await self._send_daily_report(
                yesterday,
                appointments_count,
                info_reservas_count,
                missing_details,
                info_details or [],
                consumption_summary
            )
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte diario: {e}", exc_info=True)
    
    async def _count_appointments(self, date) -> int:
        """Cuenta las reservas de una fecha específica"""
        query = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE DATE(starts_at) = %s
              AND (status IS NULL OR status NOT IN ('canceled', 'rejected'))
        """
        
        try:
            result = await self.db.execute_single(query, (date,))
            return result.get('total', 0) if result else 0
        except Exception as e:
            logger.error(f"❌ Error contando appointments: {e}")
            return 0
    
    async def _count_info_reservas(self, date) -> int:
        """Cuenta las filas de información completada de una fecha específica"""
        query = r"""
            SELECT COUNT(*) as total
            FROM "Informacion Reservas" ir
            WHERE (
                CASE
                    WHEN ir.raw ? 'fecha'
                         AND NULLIF(ir.raw->>'fecha', '') IS NOT NULL
                         AND ir.raw->>'fecha' ~ '^\d{2}/\d{2}/\d{4}$'
                    THEN to_date(ir.raw->>'fecha', 'DD/MM/YYYY')
                    ELSE DATE(ir.created_at)
                END
            ) = %s
        """
        
        try:
            result = await self.db.execute_single(query, (date,))
            return result.get('total', 0) if result else 0
        except Exception as e:
            logger.error(f"❌ Error contando Informacion Reservas: {e}")
            return 0
    
    async def _get_info_reservas_details(self, date) -> List[Dict[str, Any]]:
        """Obtiene detalles de las filas de información completada"""
        query = r"""
            WITH info AS (
                SELECT 
                    ir.id,
                    ir.created_at,
                    ir.raw,
                    CASE
                        WHEN ir.raw ? 'fecha'
                             AND NULLIF(ir.raw->>'fecha', '') IS NOT NULL
                             AND ir.raw->>'fecha' ~ '^\d{2}/\d{2}/\d{4}$'
                        THEN to_date(ir.raw->>'fecha', 'DD/MM/YYYY')
                        ELSE DATE(ir.created_at)
                    END AS target_date
                FROM "Informacion Reservas" ir
            )
            SELECT
                info.id::text AS info_id,
                info.created_at,
                info.target_date,
                info.raw->>'fecha' AS fecha_formulario,
                info.raw->>'nombre_cliente' AS nombre_cliente,
                info.raw->>'telefono' AS telefono,
                info.raw->>'productos' AS productos,
                info.raw
            FROM info
            WHERE info.target_date = %s
            ORDER BY info.created_at ASC
        """
        
        try:
            rows = await self.db.execute_query(query, (date,))
            return rows or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo detalles de Informacion Reservas: {e}")
            return []
    
    async def _get_consumption_summary(self, reservation_ids: List[str]) -> Dict[str, List[str]]:
        """Obtiene un resumen de consumo por reserva desde reservation_consumption."""
        if not reservation_ids:
            return {}
        
        query = """
            SELECT 
                reservation_id,
                item_name,
                item_sku,
                SUM(quantity) AS total_qty
            FROM reservation_consumption
            WHERE reservation_id = ANY(%s)
              AND quantity IS NOT NULL
            GROUP BY reservation_id, item_name, item_sku
            ORDER BY reservation_id, item_name
        """
        
        try:
            rows = await self.db.execute_query(query, (reservation_ids,))
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de consumo: {e}")
            return {}
        
        summary: Dict[str, List[str]] = {}
        for row in rows or []:
            reservation_id = row.get("reservation_id")
            if not reservation_id:
                continue
            qty = row.get("total_qty") or row.get("quantity") or 0
            if qty is None:
                qty = 0
            if isinstance(qty, Decimal):
                qty_value = float(qty)
            else:
                qty_value = qty
            try:
                if int(float(qty_value)) == float(qty_value):
                    qty_display = str(int(float(qty_value)))
                else:
                    qty_display = f"{float(qty_value):.2f}".rstrip("0").rstrip(".")
            except Exception:
                qty_display = str(qty)
            name = row.get("item_name") or row.get("item_sku") or "Producto"
            if reservation_id not in summary:
                summary[reservation_id] = []
            summary[reservation_id].append(f"{qty_display} x {name}")
        return summary
    
    async def _get_missing_reservas(self, date, info_entries: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene detalles de las reservas que NO tienen información completada
        cruzando fecha + hora entre Booknetic y el formulario.
        """
        appointments_query = """
            SELECT 
                a.id::text as appointment_id,
                a.starts_at,
                a.customer_name,
                a.raw->>'customer_phone_number' as phone,
                a.service_name,
                a.raw->>'start_date' as start_date_raw,
                a.raw
            FROM booknetic_appointments a
            WHERE DATE(a.starts_at) = %s
              AND (a.status IS NULL OR a.status NOT IN ('canceled', 'rejected'))
            ORDER BY a.starts_at
        """
        
        try:
            appointments = await self.db.execute_query(appointments_query, (date,))
            if info_entries is None:
                info_entries = await self._get_info_reservas_details(date)
            missing = self._match_reservas_by_datetime(date, appointments or [], info_entries or [])
            return missing
        except Exception as e:
            logger.error(f"❌ Error obteniendo reservas faltantes: {e}", exc_info=True)
            return []

    def _match_reservas_by_datetime(
        self,
        target_date,
        appointments: List[Dict[str, Any]],
        info_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cruza reservas usando fecha/hora local y registra los valores utilizados."""
        info_slots = []
        for entry in info_entries:
            if isinstance(entry, dict):
                entry.pop("_matched_appointment", None)
            dt_details = self._extract_info_datetime(entry)
            info_slots.append({
                "entry": entry,
                "local_dt": dt_details["datetime"],
                "fecha_text": dt_details["fecha_text"],
                "hora_text": dt_details["hora_text"],
                "parsed_date": dt_details["parsed_date"],
                "parsed_time": dt_details["parsed_time"]
            })
        
        if info_slots:
            logger.info(f"🧾 Información Reservas ({len(info_slots)}) para {target_date}:")
            for idx, slot in enumerate(info_slots, 1):
                entry = slot["entry"]
                raw_data = self._ensure_dict(entry.get("raw"))
                horario_raw = raw_data.get("horario_salida") or raw_data.get("hora_salida")
                logger.info(
                    f"   - #{idx} {entry.get('nombre_cliente') or 'Sin nombre'} | "
                    f"fecha_form='{slot['fecha_text'] or entry.get('fecha_formulario')}' | "
                    f"hora_form='{slot['hora_text'] or horario_raw}' | "
                    f"datetime_local={slot['local_dt']} | created_at={entry.get('created_at')}"
                )
        else:
            logger.info(f"🧾 Información Reservas: 0 filas para {target_date}")
        
        valid_info = sum(1 for slot in info_slots if slot["local_dt"] is not None)
        logger.info(
            f"ℹ️ Formularios con fecha/hora válida: {valid_info}/{len(info_slots)} "
            f"(tolerancia {self.match_tolerance_minutes} min)"
        )
        
        used_slots = set()
        missing = []
        matched = 0
        
        logger.info(f"📅 Booknetic Appointments ({len(appointments)}) para {target_date}:")
        for appt in appointments:
            appt_dt = self._appointment_local_datetime(appt)
            appt["local_dt"] = appt_dt
            hora_local = appt_dt.strftime("%H:%M") if appt_dt else "N/A"
            hora_raw = self._extract_hour_from_text(appt.get("start_date_raw"))
            logger.info(
                f"   - {appt.get('customer_name') or 'Sin nombre'} | "
                f"starts_at={appt.get('starts_at')} | local={appt_dt} | "
                f"start_date_raw={appt.get('start_date_raw')} | hora_raw={hora_raw} | "
                f"hora_local={hora_local} | servicio={appt.get('service_name')}"
            )
            matched_slot = self._find_matching_slot(appt_dt, info_slots, used_slots)
            if matched_slot is not None:
                used_slots.add(matched_slot)
                matched += 1
                info_entry = info_slots[matched_slot]["entry"]
                info_entry["_matched_appointment"] = self._build_appointment_snapshot(appt, appt_dt)
            else:
                missing.append(appt)
        
        logger.info(f"🔗 Coincidencias por fecha/hora: {matched}/{len(appointments)}")
        
        if missing:
            logger.info("⚠️ Reservas sin información tras cruzar fecha/hora:")
            for appt in missing:
                logger.info(
                    f"   - {appt.get('customer_name') or 'Sin nombre'} | "
                    f"local={appt.get('local_dt')} | start_date_raw={appt.get('start_date_raw')} | "
                    f"servicio={appt.get('service_name')}"
                )
        else:
            logger.info("✅ Todas las reservas tienen información según fecha/hora.")
        
        return missing

    def _find_matching_slot(
        self,
        appt_dt: Optional[datetime],
        info_slots: List[Dict[str, Any]],
        used_slots: set
    ) -> Optional[int]:
        """Retorna el índice del formulario que coincide con la reserva."""
        if appt_dt is None:
            return None
        
        for idx, slot in enumerate(info_slots):
            if idx in used_slots:
                continue
            info_dt = slot["local_dt"]
            if not info_dt:
                continue
            if self._within_tolerance(appt_dt, info_dt):
                return idx
        return None

    def _appointment_local_datetime(self, appt: Dict[str, Any]) -> Optional[datetime]:
        """Convierte start_date_raw (preferido) o starts_at a la zona horaria configurada."""
        starts_at = appt.get("starts_at")
        reference_date = None
        if starts_at:
            try:
                if starts_at.tzinfo is None:
                    starts_at = pytz.UTC.localize(starts_at)
                reference_date = starts_at.astimezone(self.timezone).date()
            except Exception:
                reference_date = None
        raw_text = self._clean_str(appt.get("start_date_raw"))
        if raw_text:
            raw_dt = self._parse_booknetic_raw_datetime(raw_text, reference_date)
            if raw_dt:
                return raw_dt
        if starts_at:
            try:
                if starts_at.tzinfo is None:
                    starts_at = pytz.UTC.localize(starts_at)
                return starts_at.astimezone(self.timezone)
            except Exception:
                return starts_at
        return None

    def _within_tolerance(self, dt1: datetime, dt2: datetime) -> bool:
        """Evalúa si dos datetimes están dentro de la tolerancia configurada."""
        if not dt1 or not dt2:
            return False
        diff = abs((dt1 - dt2).total_seconds())
        return diff <= self.match_tolerance_seconds

    def _build_info_details_section(
        self,
        info_details: List[Dict[str, Any]],
        consumption_summary: Dict[str, List[str]]
    ) -> str:
        """Construye texto con el detalle de información registrada."""
        if not info_details:
            return ""
        
        lines = []
        limit = 8
        for idx, entry in enumerate(info_details[:limit], 1):
            customer = entry.get("nombre_cliente") or "Sin nombre"
            dt_info = self._extract_info_datetime(entry)
            
            fecha_obj = dt_info.get("parsed_date")
            fecha_str = None
            if fecha_obj and hasattr(fecha_obj, "strftime"):
                fecha_str = fecha_obj.strftime("%d/%m/%Y")
            elif entry.get("target_date") and hasattr(entry.get("target_date"), "strftime"):
                fecha_str = entry["target_date"].strftime("%d/%m/%Y")
            else:
                fecha_str = dt_info.get("fecha_text") or "-"
            
            hora_obj = dt_info.get("parsed_time")
            if isinstance(hora_obj, dt_time):
                hora_str = hora_obj.strftime("%H:%M")
            else:
                hora_str = self._extract_hour_from_text(dt_info.get("hora_text")) \
                    or self._extract_hour_from_text(self._ensure_dict(entry.get("raw")).get("horario_salida")) \
                    or "-"
            
            reservation_id = entry.get("info_id")
            items = []
            if reservation_id and consumption_summary.get(reservation_id):
                items = consumption_summary[reservation_id]
            else:
                items = self._extract_raw_consumption_items(self._ensure_dict(entry.get("raw")))
            if not items:
                items = ["Sin consumo registrado"]
            
            lines.append(
                f"{idx}. {customer}\n"
                f"   🕘 {fecha_str} {hora_str}\n"
                f"   🧾 Consumo: {', '.join(items)}\n"
            )

            match = entry.get("_matched_appointment")
            if match:
                book_line = [
                    match.get("customer_name") or "Reserva",
                    match.get("service"),
                    match.get("people_text"),
                    match.get("payment_text"),
                ]
                book_line = [segment for segment in book_line if segment and segment != "Sin dato"]
                lines.append(f"   ↔ Booknetic: {' • '.join(book_line)}\n")
                extras = match.get("extras") or []
                if extras:
                    lines.append(f"      Extras: {', '.join(extras)}\n")
            else:
                lines.append("   ↔ Booknetic: ⚠️ No se identificó la reserva en Booknetic.\n")
        
        remaining = len(info_details) - limit
        if remaining > 0:
            lines.append(f"... y {remaining} reservas más con información completada.\n")
        
        return "".join(lines)

    def _extract_raw_consumption_items(self, raw_dict: Dict[str, Any]) -> List[str]:
        """Extrae consumos directamente desde el JSON crudo."""
        if not raw_dict:
            return []
        items: List[str] = []
        productos_text = self._clean_str(raw_dict.get("productos"))
        if productos_text:
            items.append(productos_text)
        
        for key, value in raw_dict.items():
            if not isinstance(key, str):
                continue
            lowered = key.lower()
            if not any(lowered.startswith(prefix) for prefix in self.consumption_prefixes):
                continue
            qty = self._parse_quantity_value(value)
            if qty <= 0:
                continue
            alias_match = re.search(r"\[(.+?)\]", lowered)
            alias = alias_match.group(1) if alias_match else lowered
            name = alias.replace("_", " ").strip()
            name = name.title()
            items.append(f"{qty} x {name}")
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_items = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            unique_items.append(item)
        return unique_items

    def _parse_quantity_value(self, value: Any) -> int:
        """Normaliza la cantidad a entero."""
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        text = self._clean_str(value)
        if not text:
            return 0
        text = re.sub(r"[^0-9.-]", "", text)
        if not text:
            return 0
        try:
            return int(float(text))
        except Exception:
            return 0

    def _extract_info_datetime(self, info_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene la fecha/hora local a partir del JSON del formulario."""
        raw_dict = self._ensure_dict(info_entry.get("raw"))
        normalized = {str(k).strip().lower(): v for k, v in raw_dict.items()} if raw_dict else {}
        
        fecha_text = self._first_non_empty_value(normalized, self.form_date_keys)
        if not fecha_text:
            fecha_text = info_entry.get("fecha_formulario")
        date_obj = self._parse_date_value(fecha_text)
        if not date_obj:
            target_date = info_entry.get("target_date")
            if isinstance(target_date, datetime):
                date_obj = target_date.date()
            elif hasattr(target_date, "year"):
                date_obj = target_date
        
        hora_text = self._first_non_empty_value(normalized, self.form_time_keys)
        if not hora_text and normalized:
            hora_text = self._find_value_with_keywords(normalized, ["hora", "salida"])
        if not hora_text and normalized:
            hora_text = self._find_value_with_keywords(normalized, ["hora"])
        time_obj = self._parse_time_value(hora_text)
        
        local_dt = None
        if date_obj and time_obj:
            local_dt = self._localize_datetime(date_obj, time_obj)
        
        return {
            "datetime": local_dt,
            "fecha_text": fecha_text,
            "hora_text": hora_text,
            "parsed_date": date_obj,
            "parsed_time": time_obj
        }

    def _ensure_dict(self, raw_value: Any) -> Dict[str, Any]:
        """Convierte el JSONB a dict."""
        if raw_value is None:
            return {}
        if isinstance(raw_value, dict):
            return raw_value
        try:
            return json.loads(raw_value)
        except Exception:
            return {}

    def _first_non_empty_value(self, data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """Retorna el primer valor no vacío según una lista de claves."""
        for key in keys:
            value = data.get(key)
            text = self._clean_str(value)
            if text:
                return text
        return None

    def _find_value_with_keywords(self, data: Dict[str, Any], keywords: List[str]) -> Optional[str]:
        """Busca el primer valor cuya clave contenga todos los keywords."""
        for key, value in data.items():
            lowered = key.lower()
            if all(keyword in lowered for keyword in keywords):
                text = self._clean_str(value)
                if text:
                    return text
        return None

    def _clean_str(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _parse_date_value(self, text: Optional[str]):
        """Parsea la fecha en distintos formatos."""
        if not text:
            return None
        text = text.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_time_value(self, text: Optional[str]) -> Optional[dt_time]:
        """Parsea la hora soportando distintos formatos."""
        if not text:
            return None
        cleaned = str(text).strip().lower()
        cleaned = cleaned.replace(".", ":")
        cleaned = cleaned.replace("hrs", "")
        cleaned = cleaned.replace("hr", "")
        cleaned = cleaned.replace("horas", "")
        cleaned = cleaned.replace("hs", "")
        cleaned = cleaned.replace("hor", "")
        cleaned = cleaned.strip()
        
        match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", cleaned, re.IGNORECASE)
        if not match:
            return None
        
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)
        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
        hour = hour % 24
        minute = minute % 60
        return dt_time(hour=hour, minute=minute)

    def _localize_datetime(self, date_obj, time_obj) -> datetime:
        """Combina fecha/hora en zona horaria configurada."""
        naive = datetime.combine(date_obj, time_obj)
        try:
            return self.timezone.localize(naive)
        except Exception:
            return naive

    def _parse_booknetic_raw_datetime(self, text: Optional[str], reference_date=None) -> Optional[datetime]:
        """Parsea la cadena raw->>'start_date' (ej: '14/02/2026 19:00')."""
        if not text:
            return None
        text = text.strip()
        for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M"):
            try:
                naive = datetime.strptime(text, fmt)
                return self.timezone.localize(naive)
            except ValueError:
                continue
        # Intentar extraer solo hora cuando venga sin fecha
        match = re.search(r"(\d{1,2}):(\d{2})", text)
        if match:
            hour = int(match.group(1)) % 24
            minute = int(match.group(2)) % 60
            base_date = reference_date or datetime.now(self.timezone).date()
            naive = datetime.combine(base_date, dt_time(hour=hour, minute=minute))
            return self.timezone.localize(naive)
        return None

    def _extract_hour_from_text(self, text: Optional[str]) -> Optional[str]:
        """Devuelve la hora HH:MM encontrada en un texto."""
        if not text:
            return None
        match = re.search(r"(\d{1,2}):(\d{2})", str(text))
        if not match:
            return None
        hour = int(match.group(1)) % 24
        minute = int(match.group(2)) % 60
        return f"{hour:02d}:{minute:02d}"

    def _build_appointment_snapshot(
        self,
        appt: Dict[str, Any],
        local_dt: Optional[datetime]
    ) -> Dict[str, Any]:
        """Resumen amigable de una reserva de Booknetic."""
        raw = self._ensure_dict(appt.get("raw"))
        people = self._extract_people_count_from_appointment(appt, raw)
        payment_value, payment_text = self._extract_payment_amount(appt, raw)
        extras_list = self._extract_booknetic_extras(raw, appt.get("extras"))
        service = appt.get("service_name") or raw.get("service") or "Reserva"
        customer = appt.get("customer_name") or raw.get("customer") or "Sin nombre"
        return {
            "appointment_id": appt.get("appointment_id"),
            "customer_name": customer,
            "service": service,
            "people": people,
            "people_text": f"{people} pax" if people else "Sin dato",
            "payment_value": payment_value,
            "payment_text": payment_text,
            "extras": extras_list,
            "extras_text": ", ".join(extras_list) if extras_list else "",
            "local_dt": local_dt,
            "start_date_raw": appt.get("start_date_raw") or raw.get("start_date"),
            "phone": appt.get("phone") or raw.get("customer_phone_number"),
        }

    def _extract_people_count_from_appointment(self, appt: Dict[str, Any], raw: Dict[str, Any]) -> Optional[int]:
        """Obtiene el número de clientes."""
        candidates = [
            appt.get("num_people"),
            appt.get("people"),
            appt.get("persons"),
            appt.get("quantity"),
            raw.get("num_people"),
            raw.get("people"),
            raw.get("persons"),
            raw.get("personas"),
            raw.get("cantidad_personas"),
            raw.get("numero_personas"),
            raw.get("total_personas"),
            raw.get("cant_personas"),
            raw.get("number_of_people"),
            raw.get("people_count"),
        ]
        for cand in candidates:
            count = self._parse_int_value(cand)
            if count:
                return count
        service_text = appt.get("service_name") or raw.get("service")
        return self._extract_people_from_text(service_text)

    def _extract_people_from_text(self, text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"(\d+)\s*(?:personas|people|pax)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"^(\d+)$", text.strip()) if isinstance(text, str) else None
        if match:
            return int(match.group(1))
        return None

    def _extract_payment_amount(self, appt: Dict[str, Any], raw: Dict[str, Any]) -> (Optional[float], str):
        """Obtiene el monto total pagado."""
        candidates = [
            appt.get("total_price"),
            appt.get("price"),
            appt.get("total"),
            appt.get("payment_amount"),
            raw.get("total_price"),
            raw.get("total"),
            raw.get("precio_total"),
            raw.get("payment_total"),
            raw.get("total_payment"),
            raw.get("total_amount"),
            raw.get("total_pago"),
            raw.get("payment"),
        ]
        for cand in candidates:
            amount = self._parse_float_value(cand)
            if amount is not None and amount > 0:
                return amount, self._format_currency(amount)
        return None, "Sin dato"

    def _extract_booknetic_extras(self, raw: Dict[str, Any], fallback) -> List[str]:
        """Formatea extras desde el JSON de Booknetic."""
        extras_items: List[str] = []
        sources = []
        if raw:
            for key in (
                "extras",
                "extras_list",
                "extra_services",
                "extras_selected",
                "extras_details",
                "extras_formatted",
                "extras_data"
            ):
                if raw.get(key):
                    sources.append(raw.get(key))
            text_keys = ["extras_text", "extras_description"]
            for key in text_keys:
                if raw.get(key):
                    extras_items.append(str(raw.get(key)))
        if fallback:
            sources.append(fallback)
        for source in sources:
            extras_items.extend(self._normalize_extras_source(source))
        # deduplicate
        seen = set()
        unique = []
        for item in extras_items:
            clean = item.strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            unique.append(clean)
        return unique

    def _normalize_extras_source(self, source: Any) -> List[str]:
        """Normaliza distintas estructuras de extras."""
        items: List[str] = []
        if source is None:
            return items
        data = source
        if isinstance(source, str):
            source = source.strip()
            if not source:
                return items
            try:
                data = json.loads(source)
            except Exception:
                items.append(source)
                return items
        if isinstance(data, list):
            for element in data:
                if isinstance(element, dict):
                    name = element.get("title") or element.get("name") or element.get("label")
                    qty = element.get("quantity") or element.get("qty") or element.get("amount") or 1
                    qty = self._parse_int_value(qty) or 1
                    if name:
                        items.append(f"{qty} x {name}")
                else:
                    items.append(str(element))
        elif isinstance(data, dict):
            for key, value in data.items():
                qty = 1
                name = key
                if isinstance(value, dict):
                    qty = self._parse_int_value(value.get("quantity")) or self._parse_int_value(value.get("qty")) or 1
                elif isinstance(value, (int, float, str)):
                    qty = self._parse_int_value(value) or 1
                items.append(f"{qty} x {str(name)}")
        else:
            items.append(str(data))
        return items

    def _parse_int_value(self, value: Any) -> Optional[int]:
        """Convierte un valor a entero, si es posible."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        text = self._clean_str(value)
        if not text:
            return None
        text = re.sub(r"[^0-9-]", "", text)
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _parse_float_value(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        text = self._clean_str(value)
        if not text:
            return None
        text = text.replace(".", "").replace(",", ".")
        text = re.sub(r"[^0-9.-]", "", text)
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _format_currency(self, value: Optional[float]) -> str:
        if value is None:
            return "Sin dato"
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return str(value)
        formatted = f"${amount:,.0f}".replace(",", ".")
        return f"CLP {formatted}"
    
    async def _send_daily_report(
        self, 
        date, 
        appointments_count: int, 
        info_count: int,
        missing_details: List[Dict[str, Any]],
        info_details: List[Dict[str, Any]],
        consumption_summary: Dict[str, List[str]]
    ) -> None:
        """Envía el reporte diario por Email"""
        
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
        
        if info_details:
            info_section = self._build_info_details_section(info_details, consumption_summary)
            if info_section:
                message += "\n" + "="*40 + "\n"
                message += "🧾 INFORMACIÓN REGISTRADA:\n\n"
                message += info_section
        else:
            message += "\n⚠️ No se registró información en el formulario."
        
        message += f"\n\n📊 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        
        # Enviar por WhatsApp (DESHABILITADO)
        # try:
        #     await self.send_notification(
        #         message=message,
        #         priority="high",
        #         channel="whatsapp"
        #     )
        #     logger.info("✅ Reporte diario enviado por WhatsApp")
        # except Exception as e:
        #     logger.error(f"❌ Error enviando reporte por WhatsApp: {e}")
        
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

