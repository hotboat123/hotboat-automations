"""
Script para revisar el reporte de una fecha específica
Uso: python scripts/review_date_report.py 2025-11-17
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config
from app.logger import logger
from app.monitors.daily_summary_monitor import DailySummaryMonitor
from app.notifications.manager import NotificationManager


async def review_date(target_date_str: str = None):
    """Revisa y envía el reporte de una fecha específica"""
    
    # Si no se proporciona fecha, usar ayer
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"❌ Formato de fecha inválido: {target_date_str}")
            logger.info("💡 Formato correcto: YYYY-MM-DD (ej: 2025-11-17)")
            return
    else:
        target_date = datetime.now().date() - timedelta(days=1)
        logger.info("📅 No se especificó fecha, usando ayer")
    
    logger.info(f"📊 Revisando reporte del {target_date.strftime('%d/%m/%Y')}...")
    
    settings = get_settings()
    config = load_yaml_config()
    
    # Inicializar notificaciones
    notification_manager = NotificationManager(settings, config)
    await notification_manager.initialize()
    
    # Crear monitor
    monitor_config = config.get("monitors", {}).get("daily_summary", {})
    monitor = DailySummaryMonitor(settings, monitor_config, notification_manager)
    await monitor.initialize()
    
    # Esperar un poco
    await asyncio.sleep(2)
    
    try:
        # Contar reservas
        logger.info("🔍 Contando reservas...")
        appointments_count = await monitor._count_appointments(target_date)
        logger.info(f"📅 Reservas del día: {appointments_count}")
        
        # Contar información
        logger.info("🔍 Contando información completada...")
        info_count = await monitor._count_info_reservas(target_date)
        logger.info(f"📝 Información completada: {info_count}")
        
        # Mostrar detalle de la información completada
        logger.info("🔍 Revisando detalle de información completada...")
        info_details = await monitor._get_info_reservas_details(target_date)
        reservation_ids = [entry.get("info_id") for entry in info_details if entry.get("info_id")]
        consumption_summary = await monitor._get_consumption_summary(reservation_ids)
        if info_details:
            logger.info(f"🧾 Detalle ({len(info_details)} filas):")
            for entry in info_details:
                logger.info(
                    "   - {cliente} | fecha_form='{fecha_form}' | target_date={target} | created_at={created}".format(
                        cliente=entry.get("nombre_cliente") or "Sin nombre",
                        fecha_form=entry.get("fecha_formulario") or "N/A",
                        target=entry.get("target_date"),
                        created=entry.get("created_at")
                    )
                )
                match = entry.get("_matched_appointment")
                if match:
                    logger.info(
                        "      ↔ Booknetic: {nombre} | {service} | {people} | {payment}".format(
                            nombre=match.get("customer_name") or "Reserva",
                            service=match.get("service") or "Sin servicio",
                            people=match.get("people_text") or "Sin dato",
                            payment=match.get("payment_text") or "Sin dato"
                        )
                    )
                    extras = match.get("extras") or []
                    if extras:
                        logger.info(f"         Extras: {', '.join(extras)}")
                else:
                    logger.info("      ↔ Booknetic: No se encontró coincidencia.")
        else:
            logger.info("⚠️ No se encontró información completada para esa fecha.")
        
        if consumption_summary:
            logger.info("🧾 Consumo detectado por reserva:")
            for entry in info_details:
                info_id = entry.get("info_id")
                if not info_id:
                    continue
                items = consumption_summary.get(info_id)
                if not items:
                    continue
                logger.info(f"   - {entry.get('nombre_cliente') or 'Sin nombre'}: {', '.join(items)}")
        else:
            logger.info("⚠️ No hay consumo registrado en reservation_consumption para esa fecha.")
        
        # Obtener faltantes
        logger.info("🔍 Buscando reservas faltantes...")
        missing = await monitor._get_missing_reservas(target_date, info_details)
        logger.info(f"⚠️  Reservas faltantes: {len(missing)}")
        
        # Mostrar detalles en consola
        if missing:
            logger.info("\n" + "="*50)
            logger.info("📋 RESERVAS SIN COMPLETAR:")
            logger.info("="*50)
            for i, reserva in enumerate(missing, 1):
                customer = reserva.get('customer_name', 'Sin nombre')
                phone = reserva.get('phone', 'Sin teléfono')
                service = reserva.get('service_name', 'Sin servicio')
                starts_at = reserva.get('starts_at')
                
                if starts_at:
                    if isinstance(starts_at, str):
                        try:
                            starts_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
                        except:
                            pass
                    if isinstance(starts_at, datetime):
                        time_str = starts_at.strftime("%H:%M")
                    else:
                        time_str = str(starts_at)
                else:
                    time_str = "N/A"
                
                logger.info(f"\n{i}. {time_str} - {customer}")
                logger.info(f"   📞 {phone}")
                logger.info(f"   🚤 {service}")
            logger.info("="*50 + "\n")
        else:
            logger.info("✅ ¡Todas las reservas tienen información completada!")
        
        # Preguntar si quiere enviar el reporte
        logger.info(f"\n📤 ¿Enviar reporte del {target_date.strftime('%d/%m/%Y')} por Email?")
        logger.info("   (El reporte se enviará automáticamente)")
        
        # Enviar reporte
        await monitor._send_daily_report(
            target_date,
            appointments_count,
            info_count,
            missing,
            info_details,
            consumption_summary
        )
        
        logger.info("✅ Reporte enviado! Revisa tu Email")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    
    await notification_manager.close()


if __name__ == "__main__":
    # Obtener fecha del argumento de línea de comandos
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    if date_arg:
        logger.info(f"📅 Fecha especificada: {date_arg}")
    else:
        logger.info("💡 Uso: python scripts/review_date_report.py YYYY-MM-DD")
        logger.info("💡 Ejemplo: python scripts/review_date_report.py 2025-11-17")
        logger.info("💡 Si no especificas fecha, se usará ayer\n")
    
    asyncio.run(review_date(date_arg))

