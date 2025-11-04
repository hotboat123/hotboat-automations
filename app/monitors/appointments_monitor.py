"""
Monitor de Appointments (Reservas)
"""
from typing import Dict, List, Any, Set
from datetime import datetime, timedelta
import pytz

from app.monitors.base_monitor import BaseMonitor
from app.logger import logger


class AppointmentsMonitor(BaseMonitor):
    """Monitorea cambios en las reservas"""
    
    async def check(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de las reservas
        Retorna un diccionario con información de las reservas
        """
        # Obtener todas las reservas activas (próximas y recientes)
        query = """
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
            FROM appointments
            WHERE appointment_date >= CURRENT_DATE - INTERVAL '1 day'
            ORDER BY appointment_date, start_time
        """
        
        appointments = await self.db.execute_query(query)
        
        # Crear un diccionario indexado por ID para fácil comparación
        appointments_dict = {
            str(appt['id']): appt for appt in appointments
        }
        
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
        
        date_str = appointment['appointment_date'].strftime('%d/%m/%Y')
        time_str = str(appointment.get('start_time', 'N/A'))
        
        message = f"""
🎉 **Nueva Reserva Creada**

👤 Cliente: {appointment.get('customer_name', 'N/A')}
📱 Teléfono: {appointment.get('phone_number', 'N/A')}
📅 Fecha: {date_str}
⏰ Hora: {time_str}
⛵ Embarcación: {appointment.get('boat_type', 'N/A')}
👥 Personas: {appointment.get('num_people', 'N/A')}
💰 Total: ${appointment.get('total_price', 0):,.0f}
📝 Estado: {appointment.get('status', 'N/A')}

{f"Notas: {appointment.get('notes')}" if appointment.get('notes') else ""}
        """.strip()
        
        await self.send_notification(
            message=message,
            priority="high",
            channel="telegram"
        )
        
        logger.info(f"🎉 Nueva reserva: {appointment.get('customer_name')} - {date_str}")
    
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

