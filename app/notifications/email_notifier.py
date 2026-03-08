"""
Email Notifier
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Tuple, Callable, Awaitable, Dict
from datetime import datetime
from pathlib import Path
import asyncio
import base64

try:
    import resend  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    resend = None

from app.logger import logger
from .base_notifier import BaseNotifier


class EmailNotifier(BaseNotifier):
    """Envía notificaciones por Email"""
    
    async def initialize(self):
        """Inicializa el notificador de email"""
        if not self.settings.email_enabled:
            raise ValueError("Email no está habilitado")
        
        # Verificar configuración SMTP
        self.use_smtp = bool(self.settings.smtp_host and self.settings.smtp_username)
        self.use_sendgrid = bool(self.settings.sendgrid_api_key and self.settings.sendgrid_from_email)
        self.use_resend = bool(self.settings.resend_api_key and resend is not None)
        
        if self.settings.resend_api_key and resend is None:
            logger.warning("⚠️ Resend configurado pero la librería no está instalada")
        
        if self.use_smtp:
            logger.info(
                "✅ Email SMTP configurado: %s (SSL=%s, TLS=%s)",
                self.settings.smtp_host,
                self.settings.smtp_use_ssl,
                getattr(self.settings, "smtp_use_tls", True),
            )
        if self.use_sendgrid and not self.use_smtp:
            logger.info("✅ Email SendGrid configurado")
        if self.use_resend and not (self.use_smtp or self.use_sendgrid):
            logger.info("✅ Email Resend configurado")
        
        if not any((self.use_smtp, self.use_sendgrid, self.use_resend)):
            raise ValueError("No se configuró SMTP, SendGrid ni Resend")
        
        self.recipients = self.settings.email_to_list
        if not self.recipients:
            raise ValueError("EMAIL_TO no configurado")
        
        self.resend_from_email = self.settings.resend_from_email or self.settings.email_from
        if self.use_resend and not self.resend_from_email:
            raise ValueError("RESEND_FROM_EMAIL o EMAIL_FROM no configurado para Resend")
    
    async def send(self, message: str, priority: str = "medium", attachments: Optional[List[Dict]] = None):
        """
        Envía un email
        
        Args:
            message: Mensaje del email
            priority: Prioridad del mensaje
            attachments: Lista de diccionarios con 'path', 'filename', 'content_type' (opcional)
        """
        if not self.should_send(priority):
            return
        
        subject = self._get_subject(priority)
        html_body = self._format_html(message, priority)
        
        senders: List[Tuple[str, Callable[[str, str, Optional[List[Dict]]], Awaitable[None]]]] = []
        if self.use_smtp:
            senders.append(("SMTP", self._send_smtp))
        if self.use_sendgrid:
            senders.append(("SendGrid", self._send_sendgrid))
        if self.use_resend:
            senders.append(("Resend", self._send_resend))
        
        last_error: Optional[Exception] = None
        for idx, (name, sender) in enumerate(senders, start=1):
            try:
                await sender(subject, html_body, attachments)
                if idx > 1:
                    logger.info(f"✅ Email enviado correctamente vía {name} (fallback)")
                return
            except Exception as exc:
                last_error = exc
                logger.error(f"❌ Error al enviar email ({name}): {exc}")
        
        if last_error:
            raise last_error
    
    def _get_subject(self, priority: str) -> str:
        """Genera el asunto del email según prioridad"""
        prefix_map = {
            "critical": "[CRÍTICO]",
            "high": "[IMPORTANTE]",
            "medium": "[INFO]",
            "low": "[INFO]"
        }
        
        prefix = prefix_map.get(priority, "[INFO]")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        return f"{prefix} HotBoat Automations - {timestamp}"
    
    def _format_html(self, message: str, priority: str) -> str:
        """Formatea el mensaje en HTML"""
        # Convertir Markdown básico a HTML
        html_message = message.replace("**", "<strong>").replace("**", "</strong>")
        html_message = html_message.replace("\n", "<br>")
        
        # Color según prioridad
        color_map = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#0dcaf0",
            "low": "#6c757d"
        }
        
        color = color_map.get(priority, "#0dcaf0")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: {color};
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #dee2e6;
                    font-size: 12px;
                    color: #6c757d;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚤 HotBoat Automations</h2>
                </div>
                <div class="content">
                    {html_message}
                </div>
                <div class="footer">
                    Este es un mensaje automático del sistema de monitoreo de HotBoat Chile.
                    <br>
                    Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def _send_smtp(self, subject: str, html_body: str, attachments: Optional[List[Dict]] = None):
        """Envía email usando SMTP"""
        use_ssl = bool(getattr(self.settings, "smtp_use_ssl", False))
        use_tls = bool(getattr(self.settings, "smtp_use_tls", True))
        if self.settings.smtp_port == 465:
            use_ssl = True
        
        msg = MIMEMultipart('mixed')
        msg['From'] = self.settings.email_from or self.settings.smtp_username
        msg['To'] = ", ".join(self.recipients)
        msg['Subject'] = subject
        
        # Adjuntar contenido HTML
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Adjuntar archivos si los hay
        if attachments:
            for attachment in attachments:
                filepath = Path(attachment['path'])
                if not filepath.exists():
                    logger.warning(f"⚠️ Archivo adjunto no encontrado: {filepath}")
                    continue
                
                filename = attachment.get('filename', filepath.name)
                content_type = attachment.get('content_type')
                
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                # Detectar tipo de contenido
                if content_type and content_type.startswith('image/'):
                    part = MIMEImage(file_data, name=filename)
                else:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
        
        async def send_once():
            def send_sync():
                host = self.settings.smtp_host
                port = self.settings.smtp_port
                timeout = 20
                
                if use_ssl:
                    with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
                        server.login(self.settings.smtp_username, self.settings.smtp_password)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(host, port, timeout=timeout) as server:
                        if use_tls:
                            server.starttls()
                        server.login(self.settings.smtp_username, self.settings.smtp_password)
                        server.send_message(msg)
            
            await asyncio.to_thread(send_sync)
        
        max_attempts = getattr(self.settings, "smtp_max_retries", 3)
        backoff = getattr(self.settings, "smtp_retry_backoff", 2)
        last_error: Optional[Exception] = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                await send_once()
                logger.debug(f"📧 Email enviado a {len(self.recipients)} destinatarios vía SMTP")
                return
            except Exception as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                wait_time = min(backoff * attempt, 10)
                logger.warning(
                    f"⚠️  Falló el envío SMTP (intento {attempt}/{max_attempts}): {exc}. "
                    f"Reintentando en {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
        
        if last_error:
            raise last_error
    
    async def _send_sendgrid(self, subject: str, html_body: str, attachments: Optional[List[Dict]] = None):
        """Envía email usando SendGrid"""
        if attachments:
            logger.warning("⚠️ Adjuntos no soportados en SendGrid, usando solo SMTP")
            raise NotImplementedError("Adjuntos no implementados para SendGrid")
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        message = Mail(
            from_email=Email(self.settings.sendgrid_from_email),
            to_emails=[To(email) for email in self.recipients],
            subject=subject,
            html_content=Content("text/html", html_body)
        )
        
        sg = SendGridAPIClient(self.settings.sendgrid_api_key)
        response = sg.send(message)
        
        logger.debug(f"📧 Email enviado vía SendGrid (status: {response.status_code})")
    
    async def _send_resend(self, subject: str, html_body: str, attachments: Optional[List[Dict]] = None):
        """Envía email usando Resend"""
        if attachments:
            logger.warning("⚠️ Adjuntos no soportados en Resend, usando solo SMTP")
            raise NotImplementedError("Adjuntos no implementados para Resend")
        if resend is None:
            raise RuntimeError("La librería resend no está instalada")
        
        payload = {
            "from": self.resend_from_email,
            "to": self.recipients,
            "subject": subject,
            "html": html_body,
        }
        
        def send_sync():
            resend.api_key = self.settings.resend_api_key
            return resend.Emails.send(payload)
        
        result = await asyncio.to_thread(send_sync)
        result_id = getattr(result, "id", None)
        if not result_id and isinstance(result, dict):
            result_id = result.get("id")
        logger.debug(f"📧 Email enviado vía Resend (id: {result_id or 'n/a'})")

