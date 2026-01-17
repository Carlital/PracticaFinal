"""Service for sending email notifications using SMTP"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from string import Template
from typing import Optional
import os

from app.core.config import Settings
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for email templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates", "emails")


class NotificationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.notification_repo = NotificationRepository(settings)

    def _load_template(self, template_name: str) -> str:
        """Load email HTML template from file"""
        template_path = os.path.join(TEMPLATES_DIR, template_name)
        if not os.path.exists(template_path):
            logger.warning(f"Template {template_name} not found, using plain text")
            return ""
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _send_smtp_email(
        self, to_email: str, subject: str, html_content: str, plain_text: str = ""
    ) -> tuple[bool, Optional[str]]:
        """
        Send email via SMTP (real email delivery)
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
            msg["To"] = to_email

            # Add plain text and HTML parts
            if plain_text:
                part1 = MIMEText(plain_text, "plain")
                msg.attach(part1)
            if html_content:
                part2 = MIMEText(html_content, "html")
                msg.attach(part2)

            # Connect to SMTP server
            logger.info(f"Connecting to SMTP server: {self.settings.smtp_host}:{self.settings.smtp_port}")
            
            # Use STARTTLS for Outlook (port 587)
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.ehlo()  # Identify ourselves to the SMTP server
                server.starttls()  # Secure the connection
                server.ehlo()  # Re-identify ourselves over TLS connection
                
                # Login to SMTP server
                logger.info(f"Logging in as {self.settings.smtp_user}")
                server.login(self.settings.smtp_user, self.settings.smtp_password)
                
                # Send email
                server.send_message(msg)
                logger.info(f"Email sent successfully to {to_email}")
                
            return True, None

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _send_simulated_email(
        self, to_email: str, subject: str, html_content: str
    ) -> tuple[bool, Optional[str]]:
        """
        Simulate email sending (for testing without real SMTP)
        Just logs the email details and returns success
        """
        logger.info(f"[SIMULATED EMAIL]")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content length: {len(html_content)} characters")
        logger.info(f"--- Email content preview ---")
        logger.info(html_content[:200] + "..." if len(html_content) > 200 else html_content)
        return True, None

    def send_email(
        self,
        user: User,
        tipo: str,
        subject: str,
        html_content: str,
        plain_text: str = "",
    ) -> Notification:
        """
        Send email and record notification in database
        """
        # Create notification record
        notification = Notification(
            user_id=user.id,
            tipo=tipo,
            asunto=subject,
            contenido=html_content,
            estado="pendiente",
        )
        notification = self.notification_repo.create(notification)

        # Send email based on mode
        if self.settings.notification_mode == "smtp":
            success, error_msg = self._send_smtp_email(
                user.email, subject, html_content, plain_text
            )
        else:
            success, error_msg = self._send_simulated_email(
                user.email, subject, html_content
            )

        # Update notification status
        if success:
            self.notification_repo.update_status(
                notification.id, "enviado", datetime.now(timezone.utc)
            )
            notification.estado = "enviado"
            notification.sent_at = datetime.now(timezone.utc)
        else:
            self.notification_repo.update_status(
                notification.id, "fallido", error_message=error_msg
            )
            notification.estado = "fallido"
            notification.error_message = error_msg

        return notification

    def send_welcome_email(self, user: User) -> Notification:
        """Send welcome email to newly registered user"""
        template_str = self._load_template("welcome.html")
        if template_str:
            html_content = Template(template_str).safe_substitute(
                nombre=user.nombre,
                email=user.email,
            )
        else:
            html_content = f"""
            <h1>¡Bienvenido al Centro Deportivo!</h1>
            <p>Hola {user.nombre},</p>
            <p>Gracias por registrarte en nuestro sistema de reservas.</p>
            <p>Ya puedes comenzar a hacer tus reservas de canchas deportivas.</p>
            """

        plain_text = f"Hola {user.nombre}, bienvenido al Centro Deportivo. Tu cuenta ha sido creada exitosamente."

        return self.send_email(
            user,
            "welcome",
            "¡Bienvenido al Centro Deportivo! 🎾",
            html_content,
            plain_text,
        )

    def send_reservation_confirmation(
        self, user: User, reservation_data: dict
    ) -> Notification:
        """Send reservation confirmation email"""
        template_str = self._load_template("reservation_confirmation.html")
        if template_str:
            html_content = Template(template_str).safe_substitute(
                nombre=user.nombre,
                cancha=reservation_data.get("cancha", "N/A"),
                deporte=reservation_data.get("deporte", "N/A"),
                fecha_inicio=reservation_data.get("fecha_inicio", "N/A"),
                fecha_fin=reservation_data.get("fecha_fin", "N/A"),
                precio=reservation_data.get("precio", "N/A"),
            )
        else:
            html_content = f"""
            <h1>Reserva Confirmada ✅</h1>
            <p>Hola {user.nombre},</p>
            <p>Tu reserva ha sido confirmada:</p>
            <ul>
                <li><strong>Cancha:</strong> {reservation_data.get('cancha', 'N/A')}</li>
                <li><strong>Deporte:</strong> {reservation_data.get('deporte', 'N/A')}</li>
                <li><strong>Inicio:</strong> {reservation_data.get('fecha_inicio', 'N/A')}</li>
                <li><strong>Fin:</strong> {reservation_data.get('fecha_fin', 'N/A')}</li>
                <li><strong>Precio:</strong> ${reservation_data.get('precio', 'N/A')}</li>
            </ul>
            <p>¡Te esperamos!</p>
            """

        return self.send_email(
            user,
            "reservation_confirmation",
            f"Reserva Confirmada - {reservation_data.get('cancha', 'Cancha')}",
            html_content,
        )

    def send_payment_confirmation(
        self, user: User, payment_data: dict
    ) -> Notification:
        """Send payment confirmation email"""
        template_str = self._load_template("payment_confirmation.html")
        if template_str:
            html_content = Template(template_str).safe_substitute(
                nombre=user.nombre,
                monto=payment_data.get("monto", "N/A"),
                moneda=payment_data.get("moneda", "USD"),
                fecha=payment_data.get("fecha", "N/A"),
                metodo=payment_data.get("metodo", "N/A"),
                cancha=payment_data.get("cancha", "N/A"),
            )
        else:
            html_content = f"""
            <h1>Pago Confirmado 💳</h1>
            <p>Hola {user.nombre},</p>
            <p>Hemos recibido tu pago exitosamente:</p>
            <ul>
                <li><strong>Monto:</strong> ${payment_data.get('monto', 'N/A')} {payment_data.get('moneda', 'USD')}</li>
                <li><strong>Fecha:</strong> {payment_data.get('fecha', 'N/A')}</li>
                <li><strong>Método:</strong> {payment_data.get('metodo', 'N/A')}</li>
                <li><strong>Cancha:</strong> {payment_data.get('cancha', 'N/A')}</li>
            </ul>
            <p>¡Gracias por tu pago!</p>
            """

        return self.send_email(
            user,
            "payment_confirmation",
            f"Pago Confirmado - ${payment_data.get('monto', '0')}",
            html_content,
        )

    def send_cancellation_notification(
        self, user: User, reservation_data: dict
    ) -> Notification:
        """Send cancellation notification email"""
        template_str = self._load_template("cancellation.html")
        if template_str:
            html_content = Template(template_str).safe_substitute(
                nombre=user.nombre,
                cancha=reservation_data.get("cancha", "N/A"),
                fecha_inicio=reservation_data.get("fecha_inicio", "N/A"),
            )
        else:
            html_content = f"""
            <h1>Reserva Cancelada</h1>
            <p>Hola {user.nombre},</p>
            <p>Tu reserva ha sido cancelada:</p>
            <ul>
                <li><strong>Cancha:</strong> {reservation_data.get('cancha', 'N/A')}</li>
                <li><strong>Fecha:</strong> {reservation_data.get('fecha_inicio', 'N/A')}</li>
            </ul>
            <p>Si necesitas ayuda, no dudes en contactarnos.</p>
            """

        return self.send_email(
            user,
            "cancellation",
            f"Reserva Cancelada - {reservation_data.get('cancha', 'Cancha')}",
            html_content,
        )
