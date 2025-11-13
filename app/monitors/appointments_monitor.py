"""
Monitor de Appointments (Reservas)
"""
import json
import re
from typing import Dict, List, Any, Set, Optional
from datetime import datetime, timedelta
import pytz

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class AppointmentsMonitor(BaseMonitor):
    """Monitorea cambios en las reservas"""
    
    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        # Override con variable de entorno si existe
        self.check_interval = settings.check_interval_appointments or self.check_interval
        self.table_name = config.get("table_name", "appointments")
        self.custom_query = config.get("query")

        timezone_name = config.get("timezone", "America/Santiago")
        try:
            self.timezone = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"⚠️ Zona horaria desconocida '{timezone_name}', usando America/Santiago")
            self.timezone = pytz.timezone("America/Santiago")
    
    async def check(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de las reservas
        Retorna un diccionario con información de las reservas
        """
        # Obtener todas las reservas activas (próximas y recientes)
        query = self.custom_query or f"""
            SELECT 
                id,
                customer_name,
                phone_number,
                appointment_date,
                start_time,
                duration_hours,
                boat_type,
                num_people,
                total_price,
                status,
                created_at,
                updated_at,
                notes
            FROM {self.table_name}
            WHERE appointment_date >= CURRENT_DATE - INTERVAL '1 day'
            ORDER BY appointment_date, start_time
        """
        
        appointments = await self.db.execute_query(query)
        
        # Normalizar datos y crear un diccionario indexado por ID
        appointments_dict: Dict[str, Dict[str, Any]] = {}
        for appt in appointments:
            normalized = self._normalize_appointment(appt)
            appointment_id = normalized.get("id")
            if not appointment_id:
                continue
            appointments_dict[str(appointment_id)] = normalized
        
        logger.debug(f"📅 {len(appointments)} reservas activas encontradas")
        
        return appointments_dict
    
    async def detect_changes(self, current_state: Dict[str, Any]) -> None:
        """
        Detecta cambios en las reservas y envía notificaciones
        """
        if self.last_state is None:
            return
        
        last_ids: Set[str] = set(self.last_state.keys())
        current_ids: Set[str] = set(current_state.keys())
        
        # Nuevas reservas
        new_ids = current_ids - last_ids
        for appt_id in new_ids:
            await self._notify_new_appointment(current_state[appt_id])
        
        # Reservas eliminadas/canceladas
        deleted_ids = last_ids - current_ids
        for appt_id in deleted_ids:
            await self._notify_cancelled_appointment(self.last_state[appt_id])
        
        # Reservas modificadas
        common_ids = last_ids & current_ids
        for appt_id in common_ids:
            last_appt = self.last_state[appt_id]
            current_appt = current_state[appt_id]
            
            if self._has_changed(last_appt, current_appt):
                await self._notify_modified_appointment(last_appt, current_appt)
        
        # Check for upcoming appointments (reminder)
        if self.config.get("notifications", {}).get("upcoming_reminder", True):
            await self._check_upcoming_reminders(current_state)
    
    def _has_changed(self, old_appt: Dict, new_appt: Dict) -> bool:
        """Verifica si una reserva ha cambiado"""
        # Campos importantes a comparar
        fields = [
            'customer_name', 'phone_number', 'appointment_date',
            'start_time', 'duration_hours', 'boat_type',
            'num_people', 'total_price', 'status'
        ]
        
        for field in fields:
            if old_appt.get(field) != new_appt.get(field):
                return True
        
        return False
    
    async def _notify_new_appointment(self, appointment: Dict):
        """Notifica sobre una nueva reserva"""
        if not self.config.get("notifications", {}).get("new_appointment", True):
            return
        
        message = self._build_new_appointment_message(appointment)
        
        await self.send_notification(
            message=message,
            priority="high",
            channel="whatsapp"
        )
        
        logger.info(
            "🎉 Nueva reserva: %s - %s",
            appointment.get('customer_name'),
            appointment.get('starts_at_local'),
        )

    def _normalize_appointment(self, appointment: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza campos para unificar datos sin importar la consulta"""
        normalized = dict(appointment)

        raw_data = normalized.get('raw')
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except json.JSONDecodeError:
                raw_data = {}
        if raw_data is None:
            raw_data = {}
        normalized['raw'] = raw_data

        normalized.setdefault('customer_name', raw_data.get('customer'))
        normalized.setdefault('customer_email', raw_data.get('customer_email'))

        phone = normalized.get('phone_number') or raw_data.get('customer_phone_number')
        normalized['phone_number'] = self._format_phone(phone)

        service_label = normalized.get('service_label') or raw_data.get('service')
        normalized['service_label'] = service_label
        normalized['boat_type'] = normalized.get('boat_type') or normalized.get('service_name') or service_label

        normalized['staff_member'] = normalized.get('staff_member') or raw_data.get('staff')
        normalized['duration'] = normalized.get('duration') or raw_data.get('duration')
        normalized['payment'] = normalized.get('payment') or raw_data.get('payment')

        num_people = normalized.get('num_people')
        if isinstance(num_people, str) and num_people.isdigit():
            num_people = int(num_people)
        if num_people is None:
            num_people = self._extract_people_count(service_label)
        normalized['num_people'] = num_people

        normalized['extras_formatted'] = self._format_extras(raw_data, normalized.get('extras'))

        starts_at_local = None
        if raw_data.get('start_date'):
            try:
                starts_at_local = datetime.strptime(raw_data['start_date'], '%d/%m/%Y %H:%M')
                starts_at_local = self.timezone.localize(starts_at_local)
            except ValueError:
                starts_at_local = None

        if starts_at_local is None:
            starts_at_local = self._to_local_datetime(normalized.get('starts_at'))

        normalized['starts_at_local'] = starts_at_local

        if starts_at_local:
            normalized.setdefault('appointment_date', starts_at_local.date())
            normalized.setdefault('start_time', starts_at_local.time())

        normalized['created_at_local'] = self._to_local_datetime(normalized.get('created_at'))

        return normalized

    def _to_local_datetime(self, value: Optional[datetime]) -> Optional[datetime]:
        if not value:
            return None
        if value.tzinfo is None:
            return self.timezone.localize(value)
        return value.astimezone(self.timezone)

    def _extract_people_count(self, service_label: Optional[str]) -> Optional[int]:
        if not service_label:
            return None

        match = re.search(r'(\d+)\s*(?:personas|people)', service_label, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r'^(\d+)$', service_label.strip()) if isinstance(service_label, str) else None
        if match:
            return int(match.group(1))

        return None

    def _format_phone(self, phone: Optional[str]) -> str:
        if not phone:
            return "N/A"

        digits = ''.join(ch for ch in str(phone) if ch.isdigit() or ch == '+')
        if digits.startswith('+'):
            return digits

        digits = digits.lstrip('0')
        if digits.startswith('56'):
            return f"+{digits}"

        if not digits:
            return "N/A"

        if not digits.startswith('56'):
            digits = f"56{digits}"

        return f"+{digits}"

    def _format_extras(self, raw_data: Dict[str, Any], explicit_extras: Optional[Any]) -> str:
        if explicit_extras:
            if isinstance(explicit_extras, (list, tuple, set)):
                extras = [str(item).strip() for item in explicit_extras if str(item).strip()]
                if extras:
                    return ', '.join(extras)
            elif isinstance(explicit_extras, str) and explicit_extras.strip():
                return explicit_extras.strip()

        extras_candidates: List[str] = []
        for key, value in raw_data.items():
            if not value:
                continue
            key_lower = key.lower()
            if 'extra' in key_lower:
                pretty_key = key.replace('_', ' ').replace('&amp;', '&').strip().title()
                extras_candidates.append(f"{pretty_key}: {value}")

        return ', '.join(extras_candidates) if extras_candidates else 'Sin extras registradas'

    def _build_new_appointment_message(self, appointment: Dict[str, Any]) -> str:
        starts_at_local: Optional[datetime] = appointment.get('starts_at_local')
        if starts_at_local:
            date_str = starts_at_local.strftime('%d/%m/%Y')
            time_str = starts_at_local.strftime('%H:%M')
        else:
            appointment_date = appointment.get('appointment_date')
            start_time = appointment.get('start_time')
            date_str = appointment_date.strftime('%d/%m/%Y') if hasattr(appointment_date, 'strftime') else str(appointment_date or 'N/A')
            time_str = start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time or 'N/A')

        created_at_local: Optional[datetime] = appointment.get('created_at_local')
        created_at_str = created_at_local.strftime('%d/%m/%Y %H:%M') if created_at_local else None

        num_people = appointment.get('num_people')
        num_people_text = str(num_people) if num_people is not None else 'N/A'

        extras_text = appointment.get('extras_formatted') or 'Sin extras registradas'
        service_label = appointment.get('service_label') or appointment.get('service_name') or 'Servicio no especificado'
        status = appointment.get('status') or 'Sin estado'
        duration = appointment.get('duration') or appointment.get('duration_hours')
        if isinstance(duration, (int, float)):
            duration_text = f"{duration}h"
        else:
            duration_text = duration or 'N/A'

        payment = appointment.get('payment') or appointment.get('total_price')
        if isinstance(payment, (int, float)):
            payment_text = f"${payment:,.0f}"
        else:
            payment_text = payment or 'Pendiente'

        phone_number = appointment.get('phone_number', 'N/A')
        email = appointment.get('customer_email')
        staff = appointment.get('staff_member') or 'Sin asignar'
        notes = appointment.get('notes') or ''

        lines = [
            "🎉 *Nueva Reserva HotBoat*",
            "",
            f"👤 Cliente: {appointment.get('customer_name', 'N/A')}",
        ]

        contact_line = f"📞 Contacto: {phone_number}"
        if email:
            contact_line += f" | {email}"
        lines.append(contact_line)

        lines.append(f"📅 Fecha: {date_str} a las {time_str}")
        lines.append(f"🛥️ Servicio: {service_label}")
        lines.append(f"👥 Personas: {num_people_text}")
        lines.append(f"➕ Extras: {extras_text}")
        lines.append(f"⏱️ Duración: {duration_text}")
        lines.append(f"💳 Pago: {payment_text}")
        lines.append(f"👨‍✈️ Staff: {staff}")
        lines.append(f"📌 Estado: {status}")
        lines.append(f"🆔 ID Reserva: {appointment.get('id')}")

        if created_at_str:
            lines.append(f"🕒 Creada: {created_at_str}")

        if notes:
            lines.append("")
            lines.append(f"📝 Notas: {notes}")

        return '\n'.join(lines)
    
    async def _notify_cancelled_appointment(self, appointment: Dict):
        """Notifica sobre una reserva cancelada"""
        if not self.config.get("notifications", {}).get("cancelled_appointment", True):
            return
        
        date_str = appointment['appointment_date'].strftime('%d/%m/%Y')
        
        message = f"""
❌ **Reserva Cancelada**

👤 Cliente: {appointment.get('customer_name', 'N/A')}
📅 Fecha: {date_str}
⏰ Hora: {appointment.get('start_time', 'N/A')}
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="medium",
            channel="telegram"
        )
        
        logger.info(f"❌ Reserva cancelada: {appointment.get('customer_name')} - {date_str}")
    
    async def _notify_modified_appointment(self, old_appt: Dict, new_appt: Dict):
        """Notifica sobre cambios en una reserva"""
        if not self.config.get("notifications", {}).get("modified_appointment", True):
            return
        
        # Detectar qué cambió
        changes = []
        
        if old_appt.get('appointment_date') != new_appt.get('appointment_date'):
            old_date = old_appt['appointment_date'].strftime('%d/%m/%Y')
            new_date = new_appt['appointment_date'].strftime('%d/%m/%Y')
            changes.append(f"Fecha: {old_date} → {new_date}")
        
        if old_appt.get('start_time') != new_appt.get('start_time'):
            changes.append(f"Hora: {old_appt.get('start_time')} → {new_appt.get('start_time')}")
        
        if old_appt.get('status') != new_appt.get('status'):
            changes.append(f"Estado: {old_appt.get('status')} → {new_appt.get('status')}")
        
        if old_appt.get('num_people') != new_appt.get('num_people'):
            changes.append(f"Personas: {old_appt.get('num_people')} → {new_appt.get('num_people')}")
        
        if not changes:
            return  # No hay cambios relevantes
        
        message = f"""
🔄 **Reserva Modificada**

👤 Cliente: {new_appt.get('customer_name', 'N/A')}
📱 Teléfono: {new_appt.get('phone_number', 'N/A')}

**Cambios:**
{chr(10).join(f"• {change}" for change in changes)}
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="medium",
            channel="telegram"
        )
        
        logger.info(f"🔄 Reserva modificada: {new_appt.get('customer_name')}")
    
    async def _check_upcoming_reminders(self, current_state: Dict[str, Any]):
        """Verifica reservas próximas y envía recordatorios"""
        reminder_hours = self.config.get("reminder_hours_before", 24)
        
        # Calcular el rango de tiempo para recordatorios
        # Chile timezone
        chile_tz = pytz.timezone('America/Santiago')
        now = datetime.now(chile_tz)
        reminder_window_start = now
        reminder_window_end = now + timedelta(hours=reminder_hours)
        
        for appt in current_state.values():
            appt_date = appt.get('appointment_date')
            appt_time = appt.get('start_time')
            
            if not appt_date or not appt_time:
                continue
            
            # Combinar fecha y hora
            appt_datetime = datetime.combine(appt_date, appt_time)
            appt_datetime = chile_tz.localize(appt_datetime)
            
            # Verificar si está en el rango de recordatorio
            if reminder_window_start <= appt_datetime <= reminder_window_end:
                # Verificar si ya se envió recordatorio (usando algún mecanismo de estado)
                # Por simplicidad, aquí solo logueamos
                hours_until = (appt_datetime - now).total_seconds() / 3600
                
                if 0 < hours_until <= 24:  # En las próximas 24 horas
                    logger.info(
                        f"⏰ Recordatorio: Reserva de {appt.get('customer_name')} "
                        f"en {hours_until:.1f} horas"
                    )

