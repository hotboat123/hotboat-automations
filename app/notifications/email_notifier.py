"""
Email Notifier
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import asyncio

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
        
        if self.use_smtp:
            logger.info(f"✅ Email SMTP configurado: {self.settings.smtp_host}")
        if self.use_sendgrid and not self.use_smtp:
            logger.info("✅ Email SendGrid configurado")
        
        if not self.use_smtp and not self.use_sendgrid:
            raise ValueError("No se configuró SMTP ni SendGrid")
        
        self.recipients = self.settings.email_to_list
        if not self.recipients:
            raise ValueError("EMAIL_TO no configurado")
    
    async def send(self, message: str, priority: str = "medium"):
        """Envía un email"""
        if not self.should_send(priority):
            return
        
        subject = self._get_subject(priority)
        html_body = self._format_html(message, priority)
        
        smtp_error = None
        if self.use_smtp:
            try:
                await self._send_smtp(subject, html_body)
                return
            except Exception as e:
                smtp_error = e
                logger.error(f"❌ Error al enviar email SMTP: {e}")
                if not self.use_sendgrid:
                    raise
                logger.info("🔁 Intentando enviar email vía SendGrid...")
        
        if self.use_sendgrid:
            try:
                await self._send_sendgrid(subject, html_body)
                if smtp_error:
                    logger.info("✅ Email enviado correctamente vía SendGrid (fallback)")
            except Exception as e:
                logger.error(f"❌ Error al enviar email con SendGrid: {e}")
                if smtp_error:
                    raise smtp_error
                raise
    
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
    
    async def _send_smtp(self, subject: str, html_body: str):
        """Envía email usando SMTP"""
        use_ssl = bool(getattr(self.settings, "smtp_use_ssl", False))
        if self.settings.smtp_port == 465:
            use_ssl = True
        
        msg = MIMEMultipart('alternative')
        msg['From'] = self.settings.email_from or self.settings.smtp_username
        msg['To'] = ", ".join(self.recipients)
        msg['Subject'] = subject
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
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
    
    async def _send_sendgrid(self, subject: str, html_body: str):
        """Envía email usando SendGrid"""
        try:
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
        
        except Exception as e:
            logger.error(f"❌ Error al enviar email con SendGrid: {e}")

