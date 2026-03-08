""" 
Monitor de Resumen Diario 
Envía un reporte cada mañana comparando reservas vs información completada 
""" 
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta, time as dt_time 
from decimal import Decimal
import asyncio 
import json 
import re 
import pytz
import unicodedata 

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
            
            # Calcular ingresos
            revenue_data = await self._calculate_revenue_for_date(yesterday)
            
            # Generar y enviar el mensaje
            await self._send_daily_report(
                yesterday,
                appointments_count,
                info_reservas_count,
                missing_details,
                info_details or [],
                consumption_summary,
                revenue_data
            )
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte diario: {e}", exc_info=True)
    
    async def _count_appointments(self, date) -> int:
        """Cuenta las reservas de una fecha específica"""
        query = """
            SELECT COUNT(*) as total
            FROM booknetic_appointments
            WHERE DATE(
                CASE
                    WHEN raw->>'start_date' IS NOT NULL 
                         AND raw->>'start_date' ~ '^\d{1,2}/\d{1,2}/\d{4}'
                    THEN TO_TIMESTAMP(raw->>'start_date', 'DD/MM/YYYY HH24:MI')
                    ELSE starts_at
                END
            ) = %s
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
                         AND ir.raw->>'fecha' ~ '^\d{1,2}/\d{1,2}/\d{4}$'
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
                             AND ir.raw->>'fecha' ~ '^\d{1,2}/\d{1,2}/\d{4}$'
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
            WHERE DATE(
                CASE
                    WHEN a.raw->>'start_date' IS NOT NULL 
                         AND a.raw->>'start_date' ~ '^\d{1,2}/\d{1,2}/\d{4}'
                    THEN TO_TIMESTAMP(a.raw->>'start_date', 'DD/MM/YYYY HH24:MI')
                    ELSE a.starts_at
                END
            ) = %s
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
        
        # Intentar matching por nombre para los que no coincidieron por fecha/hora
        if missing:
            logger.info("⚠️ Reservas sin información tras cruzar fecha/hora:")
            for appt in missing:
                logger.info(
                    f"   - {appt.get('customer_name') or 'Sin nombre'} | "
                    f"local={appt.get('local_dt')} | start_date_raw={appt.get('start_date_raw')} | "
                    f"servicio={appt.get('service_name')}"
                )
            
            # Intentar matching por nombre como fallback
            logger.info("🔍 Intentando matching por nombre de cliente...")
            matched_by_name = self._match_by_customer_name(missing, info_slots, used_slots)
            
            if matched_by_name > 0:
                logger.info(f"✅ Coincidencias adicionales por nombre: {matched_by_name}")
                # Actualizar la lista de missing
                missing = [appt for appt in missing if not any(
                    slot["entry"].get("_matched_appointment", {}).get("id") == appt.get("id")
                    for slot in info_slots
                )]
            else:
                logger.info("⚠️ No se encontraron coincidencias adicionales por nombre")
        else:
            logger.info("✅ Todas las reservas tienen información según fecha/hora.")
        
        return missing

    def _match_by_customer_name(
        self,
        appointments: List[Dict[str, Any]],
        info_slots: List[Dict[str, Any]],
        used_slots: set
    ) -> int:
        """
        Intenta hacer matching por nombre de cliente para appointments que no coincidieron por fecha/hora.
        Retorna el número de matches encontrados.
        """
        matched_count = 0
        
        for appt in appointments:
            customer_name = appt.get('customer_name', '').strip().lower()
            if not customer_name:
                continue
            
            # Normalizar nombre (quitar espacios extras, acentos, etc)
            customer_normalized = self._normalize_name(customer_name)
            
            best_match_idx = None
            best_match_score = 0
            
            for idx, slot in enumerate(info_slots):
                if idx in used_slots:
                    continue
                
                entry = slot["entry"]
                raw_data = self._ensure_dict(entry.get("raw"))
                
                # Buscar nombre en diferentes campos
                info_name = (
                    entry.get('nombre_cliente') or 
                    raw_data.get('nombre_cliente') or 
                    raw_data.get('name') or 
                    raw_data.get('nombres_adultos_(ej:_felipe,_iker,_max)') or
                    ''
                ).strip().lower()
                
                if not info_name:
                    continue
                
                info_normalized = self._normalize_name(info_name)
                
                # Calcular similitud
                score = self._calculate_name_similarity(customer_normalized, info_normalized)
                
                if score > best_match_score and score > 0.7:  # Threshold de 70% similitud
                    best_match_score = score
                    best_match_idx = idx
            
            if best_match_idx is not None:
                used_slots.add(best_match_idx)
                matched_count += 1
                info_entry = info_slots[best_match_idx]["entry"]
                appt_dt = appt.get('local_dt')
                info_entry["_matched_appointment"] = self._build_appointment_snapshot(appt, appt_dt)
                
                logger.info(
                    f"   ✓ Match por nombre: '{appt.get('customer_name')}' → "
                    f"'{info_entry.get('nombre_cliente') or 'Sin nombre'}' "
                    f"(similitud: {best_match_score:.0%})"
                )
        
        return matched_count
    
    def _normalize_name(self, name: str) -> str:
        """Normaliza un nombre para comparación"""
        import unicodedata
        
        # Quitar acentos
        name = unicodedata.normalize('NFKD', name)
        name = ''.join([c for c in name if not unicodedata.combining(c)])
        
        # Convertir a minúsculas y quitar espacios extras
        name = ' '.join(name.lower().split())
        
        return name
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calcula similitud entre dos nombres (0.0 a 1.0)
        Usa una combinación de coincidencia exacta y coincidencia parcial
        """
        if name1 == name2:
            return 1.0
        
        # Si uno contiene al otro
        if name1 in name2 or name2 in name1:
            return 0.9
        
        # Comparar palabras individuales (nombre, apellidos)
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calcular intersección
        common = words1.intersection(words2)
        total = words1.union(words2)
        
        return len(common) / len(total) if total else 0.0
    
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
                # start_date está en hora local de Chile
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
        consumption_summary: Dict[str, List[str]],
        revenue_data: Dict[str, Any] = None
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
        
        # Agregar información de ingresos
        if revenue_data and revenue_data.get('total_reservations', 0) > 0:
            total_revenue = revenue_data.get('total_revenue', 0)
            revenue_reservations = revenue_data.get('revenue_reservations', 0)
            revenue_extras = revenue_data.get('revenue_extras', 0)
            average_revenue = revenue_data.get('average_revenue', 0)
            total_payments = revenue_data.get('total_reservations', 0)
            marketing_cost = revenue_data.get('marketing_cost', 0)
            num_marketing_ads = revenue_data.get('num_marketing_ads', 0)
            operational_costs = revenue_data.get('operational_costs', {})
            operational_profit = revenue_data.get('operational_profit', 0)
            net_profit = revenue_data.get('net_profit', 0)
            net_margin = revenue_data.get('net_margin', 0)
            total_costs = revenue_data.get('total_costs', 0)
            
            message += f"""
{"="*40}
💰 INGRESOS DEL DÍA

💵 Total Reservas: ${revenue_reservations:,.0f}
🍾 Total Extras: ${revenue_extras:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💰 TOTAL INGRESOS: ${total_revenue:,.0f}

📊 Promedio por reserva: ${average_revenue:,.0f}
🧾 Pagos registrados: {total_payments}

{"="*40}
💸 COSTOS DEL DÍA

📢 Marketing: ${marketing_cost:,.0f} ({num_marketing_ads} anuncios)

🏭 Costos Operativos: ${operational_costs.get('total', 0):,.0f}
   Fijos ({total_payments} reservas × $18,000):
     • Gas: ${operational_costs.get('gas', 0):,.0f}
     • Leña: ${operational_costs.get('leña', 0):,.0f}
     • Agua: ${operational_costs.get('agua', 0):,.0f}
     • Hielo: ${operational_costs.get('hielo', 0):,.0f}
   
   Variables (extras desde BD):
     • Videos: ${operational_costs.get('videos', 0):,.0f}
     • Tablas: ${operational_costs.get('tablas', 0):,.0f}
     • Marcos: ${operational_costs.get('marcos', 0):,.0f}
     • Otros: ${operational_costs.get('otros', 0):,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 COSTOS TOTALES: ${total_costs:,.0f}

{"="*40}
📈 UTILIDAD NETA

💰 Ingresos: ${total_revenue:,.0f}
💸 Costos Totales: -${total_costs:,.0f}
━━━━━━━━━━━━━━━━━━━━━
💵 UTILIDAD NETA: ${net_profit:,.0f}
📊 Margen Neto: {net_margin:.1f}%

"""
            
            # Detalle por reserva
            details = revenue_data.get('details', [])
            if details:
                message += "DETALLE POR RESERVA:\n\n"
                for idx, detail in enumerate(details[:8], 1):
                    customer = detail.get('customer_name', 'Sin nombre')
                    num_people = detail.get('num_people', 0)
                    payment_amount = detail.get('payment_amount', 0)
                    res_total = detail.get('reservation_total', 0)
                    extras_total = detail.get('extras_total', 0)
                    total_with_extras = detail.get('total_with_extras', 0)
                    
                    appt_time = detail.get('appointment_datetime')
                    if appt_time:
                        if isinstance(appt_time, str):
                            try:
                                appt_time = datetime.fromisoformat(appt_time.replace('Z', '+00:00'))
                            except:
                                # Intentar parsear formato 'YYYY-MM-DD HH:MM:SS'
                                try:
                                    appt_time = datetime.strptime(appt_time, '%Y-%m-%d %H:%M:%S')
                                except:
                                    pass
                        time_str = appt_time.strftime("%H:%M") if isinstance(appt_time, datetime) else str(appt_time).split()[-1] if ' ' in str(appt_time) else "N/A"
                    else:
                        time_str = "N/A"
                    
                    message += f"{idx}. {time_str} - {customer}\n"
                    
                    # Mostrar información de la reserva
                    if num_people:
                        message += f"   👥 {num_people} personas\n"
                    
                    message += f"   💵 Subtotal Reserva: ${res_total:,.0f}\n"
                    
                    extras_list = detail.get('extras', [])
                    if extras_list and extras_total > 0:
                        message += f"   🍾 Extras: ${extras_total:,.0f}\n"
                        # Mostrar algunos extras
                        extras_summary = []
                        for extra in extras_list[:3]:
                            qty = extra.get('cantidad', 0)
                            nombre = extra.get('nombre', 'Item')
                            extras_summary.append(f"{qty}x {nombre}")
                        if extras_summary:
                            message += f"      ({', '.join(extras_summary)})\n"
                    
                    message += f"   💰 Total: ${total_with_extras:,.0f}\n\n"
                
                if len(details) > 8:
                    message += f"... y {len(details) - 8} reservas más.\n\n"
            
            # Advertir sobre precios faltantes
            missing_prices = revenue_data.get('missing_prices', [])
            if missing_prices:
                message += f"⚠️ Extras sin precio configurado: {', '.join(missing_prices[:5])}\n\n"
        
        message += "="*40 + "\n"
        
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
            sent = await self.send_notification(
                message=message,
                priority="high",
                channel="email"
            )
            if sent:
                logger.info("✅ Reporte diario enviado por Email")
            else:
                logger.error("❌ No se pudo enviar el reporte diario (sin canales exitosos)")
                # Permitir reintento en el próximo ciclo
                self.last_report_date = None
        except Exception as e:
            logger.error(f"❌ Error enviando reporte por Email: {e}")
            self.last_report_date = None
    
    # ========== MÉTODOS PARA CALCULAR INGRESOS ==========
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto removiendo tildes, espacios y caracteres especiales"""
        nfkd = unicodedata.normalize('NFKD', text)
        text_without_accents = ''.join([c for c in nfkd if not unicodedata.combining(c)])
        normalized = text_without_accents.lower().replace(' ', '_').replace('-', '_')
        return normalized
    
    def _get_base_prices_by_people(self) -> Dict[int, float]:
        """
        Define los precios base de las reservas según número de personas
        Estos son los precios SIN incluir extras
        """
        return {
            2: 139990,   # 2 personas
            3: 159990,   # 3 personas (estimado)
            4: 189960,   # 4 personas
            5: 194950,   # 5 personas
            6: 197940,   # 6 personas
            # Agregar más según sea necesario
        }
    
    def _find_cost_for_extra(self, extra_name: str, costs_dict: Dict[str, float]) -> float:
        """
        Busca el costo de un extra, intentando varios métodos de matching
        """
        extra_normalized = self._normalize_text(extra_name)
        
        # 1. Matching exacto
        if extra_normalized in costs_dict:
            return costs_dict[extra_normalized]
        
        # 2. Mapeo específico para casos conocidos
        mappings = {
            'tabla_1_persona': 'tabla_4_personas',
            'tabla_1': 'tabla_4_personas',
            'tabla_4': 'tabla_4_personas',
            'tabla_2': 'tabla_2_personas',
            'video_15_segundos': 'video_15_seg',
            'video_60_segundos': 'video_1_min',
            'video_1_minuto': 'video_1_min',
            'jugo_naranja': 'jugo_1l',
            'jugo_1_l': 'jugo_1l',
            'jugo_berries': 'jugo_1l',
            'jugo_natural_1lt': 'jugo_1l',
            'foto_con_marco': 'foto_con_marco',
        }
        
        if extra_normalized in mappings:
            mapped_name = mappings[extra_normalized]
            if mapped_name in costs_dict:
                return costs_dict[mapped_name]
        
        # 3. Búsqueda por palabras clave
        words = [w for w in extra_normalized.split('_') if len(w) > 2]
        
        # Buscar matches parciales
        best_match = None
        best_score = 0
        
        for bd_name, bd_cost in costs_dict.items():
            if bd_cost == 0:
                continue
            
            score = sum(1 for word in words if word in bd_name)
            if score > best_score:
                best_score = score
                best_match = bd_cost
        
        if best_score >= 1:  # Al menos una palabra coincide
            return best_match
        
        return 0
    
    def _calculate_operational_costs(
        self,
        num_reservations: int,
        extras_list: List[Dict[str, Any]],
        costs_dict: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calcula los costos operativos de las reservas usando costos de la BD
        
        Costos fijos por reserva:
        - Gas: $15,000
        - Leña: $1,000
        - Agua: $1,000
        - Hielo: $1,000
        Total fijo: $18,000 por reserva
        
        Costos variables (extras):
        - Se obtienen de la tabla "Precios Extras" columna "costo"
        """
        # Costos fijos por reserva (estos siguen hardcodeados)
        COSTO_GAS_POR_RESERVA = 15000
        COSTO_LEÑA_POR_RESERVA = 1000
        COSTO_AGUA_POR_RESERVA = 1000
        COSTO_HIELO_POR_RESERVA = 1000
        COSTO_FIJO_TOTAL = 18000  # Suma de todos los anteriores
        
        # Calcular costos fijos
        costos_fijos = num_reservations * COSTO_FIJO_TOTAL
        
        # Calcular costos variables usando la BD
        costo_videos = 0
        costo_tablas = 0
        costo_marcos = 0
        costo_otros = 0
        
        for extra in extras_list:
            extra_nombre = extra.get('nombre', '')
            cantidad = extra.get('cantidad', 0)
            nombre_normalizado = self._normalize_text(extra_nombre)
            
            # Buscar el costo usando el nuevo método inteligente
            costo_unitario = self._find_cost_for_extra(extra_nombre, costs_dict)
            costo_total_extra = cantidad * costo_unitario
            
            # Clasificar por tipo para el reporte
            if 'video' in nombre_normalizado:
                costo_videos += costo_total_extra
            elif 'tabla' in nombre_normalizado:
                costo_tablas += costo_total_extra
            elif 'marco' in nombre_normalizado or 'foto' in nombre_normalizado:
                costo_marcos += costo_total_extra
            else:
                costo_otros += costo_total_extra
        
        costos_variables = costo_videos + costo_tablas + costo_marcos + costo_otros
        costos_operativos_totales = costos_fijos + costos_variables
        
        return {
            'fijos': costos_fijos,
            'gas': num_reservations * COSTO_GAS_POR_RESERVA,
            'leña': num_reservations * COSTO_LEÑA_POR_RESERVA,
            'agua': num_reservations * COSTO_AGUA_POR_RESERVA,
            'hielo': num_reservations * COSTO_HIELO_POR_RESERVA,
            'variables': costos_variables,
            'videos': costo_videos,
            'tablas': costo_tablas,
            'marcos': costo_marcos,
            'otros': costo_otros,
            'total': costos_operativos_totales
        }
    
    def _get_category_aliases(self) -> Dict[str, List[str]]:
        """Define aliases/variantes de nombres que mapean a las mismas categorías"""
        return {
            # Champañas
            'champana_riccadona': [
                'champana_riccadonna_ruby',
                'champana_riccadonna_moscato_rose',
                'champana_riccadonna_asti',
                'champana_riccadonna',
                'riccadonna_ruby',
                'riccadonna_moscato_rose',
                'riccadonna_asti',
                'riccadonna'
            ],
            'champana_undurraga_demi_sec': [
                'champana_undurraga',
                'undurraga_demi_sec',
                'demi_sec'
            ],
            
            # Cervezas
            'cerveza_artesanal': [
                'cerveza_artesanal_ambar',
                'cerveza_artesanal_negra',
                'artesanal_ambar',
                'artesanal_negra'
            ],
            'cerveza_premium': [
                'cerveza_austral_calafate',
                'cerveza_austral_lager',
                'cerveza_kunstman_valdivia',
                'cerveza_kunstman_torobayo',
                'austral_calafate',
                'austral_lager',
                'kunstman_valdivia',
                'kunstman_torobayo'
            ],
            'cerveza_normal': [
                'cerveza_royal',
                'royal'
            ],
            
            # Vinos
            'vino_casillero_del_diablo': [
                'vino_carmenere',
                'vino_cabernet_sauvignon',
                'vino_merlot',
                'carmenere',
                'cabernet_sauvignon',
                'merlot'
            ],
            
            # Bebidas
            'lata_bebida': [
                'coca_cola',
                'coca-cola',
                'fanta',
                'sprite',
                'bebida_lata'
            ],
            'jugo_1l': [
                'jugo_mango_naranja',
                'jugo_naranja',
                'jugo_berries',
                'mango_naranja',
                'naranja',
                'berries'
            ],
            'agua_1_5l': [
                'agua',
                'agua_mineral'
            ],
            
            # Licores
            'lemon_stone': [
                'lemon_stone_normal',
                'maracuya_stone',
                'maracuya_stone_'
            ],
            
            # Extras especiales
            'romantic': [
                'modo_romantico',
                'romantico',
                'pack_romantico',
                'pack_iluminacion_velas_y_letras',  # Mapea a romantic
                'pack_iluminacion',
                'velas_y_letras',
                'iluminacion'
            ],
            
            # Fotos y videos
            'foto_con_marco': [  # Gratis - precio 0
                'foto',
                'marco',
                'fotografia'
            ],
            
            # Tablas
            'tabla_4_personas': [
                'tabla_1_persona',
                'tabla_1',
                'tabla_4'
            ],
            'tabla_2_personas': [
                'tabla_2'
            ],
            
            # Extras especiales
            'romantic': [
                'modo_romantico',
                'romantico',
                'modo_romantico'
            ],
            'video_15_seg': [
                'video_15_segundos',
                'video_15'
            ],
            'video_1_min': [
                'video_60_segundos',
                'video_60'
            ],
            
            # Otros
            'poncho': [
                'toalla_poncho'
            ]
        }
    
    async def _load_prices(self) -> tuple[Dict[str, float], Dict[str, float]]:
        """
        Carga precios Y costos desde la tabla Precios Extras
        Retorna: (prices, costs) - dos diccionarios con los precios y costos
        """
        query = 'SELECT * FROM "Precios Extras"'
        
        try:
            rows = await self.db.execute_query(query)
            prices = {}
            costs = {}
            
            for row in rows:
                raw = row.get('raw', {})
                if not raw:
                    continue
                
                extra_name = raw.get('Extra', '')
                precio_str = raw.get('Precio', '0')
                costo_str = raw.get('costo', '0')  # Nuevo: leer el costo
                
                if not extra_name:
                    continue
                
                # Limpiar precio (remover puntos y convertir)
                try:
                    precio = float(str(precio_str).replace('.', '').replace(',', '').strip())
                except (ValueError, AttributeError):
                    precio = 0
                
                # Limpiar costo (remover puntos y convertir)
                try:
                    costo = float(str(costo_str).replace('.', '').replace(',', '').strip()) if costo_str else 0
                except (ValueError, AttributeError):
                    costo = 0
                
                # Normalizar nombre del extra
                normalized = self._normalize_text(extra_name)
                prices[normalized] = precio
                costs[normalized] = costo
            
            logger.info(f"📋 Cargados {len(prices)} precios y {len(costs)} costos desde base de datos")
            
            # Agregar precios por defecto para extras gratuitos o sin precio en BD
            if 'foto_con_marco' not in prices:
                prices['foto_con_marco'] = 15000
                costs['foto_con_marco'] = 2500  # Costo del marco
            
            return prices, costs
        except Exception as e:
            logger.error(f"❌ Error cargando precios: {e}", exc_info=True)
            return {}, {}
    
    def _find_price_for_extra(
        self,
        extra_name: str,
        prices: Dict[str, float],
        category_aliases: Dict[str, List[str]]
    ) -> tuple[float, str]:
        """Encuentra el precio de un extra usando aliases y categorías"""
        extra_normalized = self._normalize_text(extra_name)
        
        if extra_normalized in prices:
            return prices[extra_normalized], extra_normalized
        
        for category, aliases in category_aliases.items():
            aliases_normalized = [self._normalize_text(alias) for alias in aliases]
            if extra_normalized in aliases_normalized:
                if category in prices:
                    return prices[category], category
        
        for category in prices.keys():
            if category in extra_normalized or extra_normalized in category:
                return prices[category], category
        
        return 0.0, ""
    
    def _extract_extras_from_json(
        self,
        raw_json: Dict[str, Any],
        prices: Dict[str, float],
        category_aliases: Dict[str, List[str]],
        missing_prices: Set[str]
    ) -> List[Dict[str, Any]]:
        """Extrae los extras del campo raw de Informacion Reservas"""
        if not raw_json:
            return []
        
        extras_list = []
        extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
        
        for key, value in raw_json.items():
            key_lower = key.lower()
            is_extra = any(key_lower.startswith(prefix) for prefix in extra_prefixes)
            
            if not is_extra:
                continue
            
            try:
                quantity = int(str(value).strip()) if value and str(value).strip() else 0
            except (ValueError, AttributeError):
                quantity = 0
            
            if quantity <= 0:
                continue
            
            alias_match = re.search(r'\[(.+?)\]', key)
            if alias_match:
                alias = alias_match.group(1)
            else:
                alias = key
            
            price, category_used = self._find_price_for_extra(alias, prices, category_aliases)
            
            if price == 0:
                missing_prices.add(alias)
            
            subtotal = price * quantity
            
            extras_list.append({
                'nombre': alias,
                'cantidad': quantity,
                'precio_unitario': price,
                'subtotal': subtotal,
                'categoria': category_used
            })
        
        return extras_list
    
    async def _calculate_revenue_for_date(self, target_date) -> Dict[str, Any]:
        """Calcula los ingresos diarios usando booknetic_appointments.payment para el costo base"""
        
        # Cargar precios, costos y aliases para extras
        prices, costs = await self._load_prices()
        category_aliases = self._get_category_aliases()
        missing_prices: Set[str] = set()
        
        # Query que cruza booknetic_appointments con Informacion Reservas
        # Usa el campo 'payment' de booknetic_appointments como precio base de la reserva
        # Usa ROW_NUMBER() para hacer matching 1 a 1 cuando hay múltiples reservas a la misma hora
        query = """
            WITH appointments_data AS (
                SELECT 
                    ba.id as appointment_id,
                    DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) as appointment_date,
                    TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI') as appointment_datetime,
                    ba.raw->>'start_date' as start_date_raw,
                    ba.status,
                    ba.raw->>'customer_name' as customer_name,
                    ba.raw->>'customer_email' as customer_email,
                    CAST(
                        REGEXP_REPLACE(
                            REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                            '[^0-9]',
                            '',
                            'g'
                        ) AS NUMERIC
                    ) as payment_amount,
                    ba.raw as appointment_raw,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')),
                                     TO_CHAR(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI'), 'HH24:MI:SS')
                        ORDER BY ba.id
                    ) as appointment_row_num
                FROM booknetic_appointments ba
                WHERE ba.raw->>'start_date' IS NOT NULL
                  AND DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = %s
            ),
            reservations_with_extras AS (
                SELECT 
                    ir.id as reservation_id,
                    TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                    ir.raw->>'horario_salida' as horario_salida,
                    ir.email,
                    ir.raw as extras_json,
                    ROW_NUMBER() OVER (
                        PARTITION BY TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY'),
                                     ir.raw->>'horario_salida'
                        ORDER BY ir.created_at ASC
                    ) as reservation_row_num
                FROM "Informacion Reservas" ir
                WHERE ir.raw->>'fecha' IS NOT NULL
            )
            SELECT 
                ad.appointment_id,
                ad.payment_amount,
                ad.appointment_date,
                ad.appointment_datetime,
                ad.start_date_raw,
                ad.status,
                ad.customer_name,
                ad.customer_email,
                r.reservation_id,
                r.email,
                r.extras_json,
                ad.appointment_raw
            FROM appointments_data ad
            LEFT JOIN reservations_with_extras r 
                ON ad.appointment_date = r.reservation_date
                AND TO_CHAR(ad.appointment_datetime, 'HH24:MI:SS') = r.horario_salida
                AND ad.appointment_row_num = r.reservation_row_num
            ORDER BY ad.appointment_datetime, ad.appointment_id
        """
        
        try:
            results = await self.db.execute_query(query, (target_date,))
            
            total_reservations = len(results)
            total_revenue_reservations = Decimal('0')
            total_revenue_extras = Decimal('0')
            
            revenue_details = []
            
            for row in results:
                # Usar el campo 'payment' de booknetic_appointments como precio base
                appointment_raw = row.get('appointment_raw', {})
                payment_amount = row.get('payment_amount', 0) or 0
                
                # El payment_amount ya es el precio final de la reserva (base - descuentos)
                reservation_total = Decimal(str(payment_amount))
                total_revenue_reservations += reservation_total
                
                # Extraer número de personas para información
                num_people = None
                people_candidates = [
                    appointment_raw.get('num_people'),
                    appointment_raw.get('people'),
                    appointment_raw.get('persons'),
                    appointment_raw.get('cantidad_personas'),
                ]
                for cand in people_candidates:
                    if cand:
                        try:
                            num_people = int(str(cand).strip())
                            if num_people > 0:
                                break
                        except (ValueError, AttributeError):
                            continue
                
                # Si no se encontró, intentar extraer del servicio
                if not num_people:
                    service = appointment_raw.get('service', '')
                    import re
                    match = re.search(r'(\d+)\s*(?:personas|people|pax)', str(service), re.IGNORECASE)
                    if match:
                        num_people = int(match.group(1))
                
                # Extraer y calcular extras SOLO de "Información Reservas"
                extras_json = row.get('extras_json')
                extras_list = self._extract_extras_from_json(
                    extras_json, 
                    prices, 
                    category_aliases,
                    missing_prices
                ) if extras_json else []
                
                extras_total = sum(extra['subtotal'] for extra in extras_list)
                total_revenue_extras += Decimal(str(extras_total))
                
                revenue_details.append({
                    'appointment_id': row.get('appointment_id'),
                    'customer_name': row.get('customer_name'),
                    'email': row.get('email'),
                    'appointment_datetime': row.get('appointment_datetime'),
                    'status': row.get('status'),
                    'num_people': num_people,
                    'payment_amount': float(payment_amount),
                    'reservation_total': float(reservation_total),
                    'extras': extras_list,
                    'extras_total': extras_total,
                    'total_with_extras': float(reservation_total) + extras_total,
                    'reservation_id': row.get('reservation_id')
                })
            
            total_revenue = total_revenue_reservations + total_revenue_extras
            average_revenue = float(total_revenue) / total_reservations if total_reservations > 0 else 0
            
            # Recopilar todos los extras del día para calcular costos operativos
            all_extras = []
            for detail in revenue_details:
                all_extras.extend(detail.get('extras', []))
            
            # Calcular costos operativos (fijos + variables) usando costos de BD
            operational_costs = self._calculate_operational_costs(total_reservations, all_extras, costs)
            
            # Obtener costos de marketing para la fecha
            marketing_costs_query = """
                SELECT 
                    COALESCE(SUM(amount_spent), 0) as total_marketing_cost,
                    COUNT(*) as num_ads
                FROM marketing_costs
                WHERE cost_date = %s
            """
            
            try:
                marketing_result = await self.db.execute_query(marketing_costs_query, (target_date,))
                if marketing_result and len(marketing_result) > 0:
                    total_marketing_cost = float(marketing_result[0].get('total_marketing_cost', 0))
                    num_marketing_ads = marketing_result[0].get('num_ads', 0)
                else:
                    total_marketing_cost = 0
                    num_marketing_ads = 0
            except Exception as e:
                logger.warning(f"No se pudieron obtener costos de marketing: {e}")
                total_marketing_cost = 0
                num_marketing_ads = 0
            
            # Calcular utilidades
            # Utilidad Operativa = Ingresos - Marketing
            operational_profit = float(total_revenue) - total_marketing_cost
            
            # Utilidad Neta = Ingresos - Marketing - Costos Operativos
            total_costs = total_marketing_cost + operational_costs['total']
            net_profit = float(total_revenue) - total_costs
            net_margin = (net_profit / float(total_revenue) * 100) if total_revenue > 0 else 0
            
            return {
                'total_reservations': total_reservations,
                'revenue_reservations': float(total_revenue_reservations),
                'revenue_extras': float(total_revenue_extras),
                'total_revenue': float(total_revenue),
                'average_revenue': average_revenue,
                'marketing_cost': total_marketing_cost,
                'num_marketing_ads': num_marketing_ads,
                'operational_costs': operational_costs,
                'operational_profit': operational_profit,
                'profit_margin': (operational_profit / float(total_revenue) * 100) if total_revenue > 0 else 0,
                'total_costs': total_costs,
                'net_profit': net_profit,
                'net_margin': net_margin,
                'details': revenue_details,
                'missing_prices': list(missing_prices)
            }
        
        except Exception as e:
            logger.error(f"❌ Error calculando ingresos: {e}", exc_info=True)
            return {
                'total_reservations': 0,
                'revenue_reservations': 0,
                'revenue_extras': 0,
                'total_revenue': 0,
                'average_revenue': 0,
                'marketing_cost': 0,
                'num_marketing_ads': 0,
                'operational_costs': {
                    'fijos': 0, 'gas': 0, 'leña': 0, 'agua': 0, 'hielo': 0,
                    'variables': 0, 'videos': 0, 'tablas': 0, 'marcos': 0, 'total': 0
                },
                'operational_profit': 0,
                'profit_margin': 0,
                'total_costs': 0,
                'net_profit': 0,
                'net_margin': 0,
                'details': [],
                'missing_prices': []
            }

