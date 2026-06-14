"""Envoi d'e-mails au plaignant — garde-fou.

N'envoie réellement QUE si SMTP_HOST est configuré. Sinon l'action métier est
enregistrée (accusé/réponse marqués envoyés) mais aucun mail n'est émis : ainsi la
démo et le dev ne déclenchent pas d'envois réels. Retourne True si un mail a été émis.
"""
import logging
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email_safe(settings, to: str, subject: str, body: str) -> bool:
    smtp_host = getattr(settings, "SMTP_HOST", None)
    if not smtp_host or not to:
        logger.info(
            f"📧 SMTP non configuré ou destinataire vide — '{subject}' vers '{to}' "
            f"enregistré mais NON envoyé."
        )
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = getattr(settings, "EMAIL_FROM", None) or getattr(settings, "SMTP_USER", "")
        msg["To"] = to
        with smtplib.SMTP(smtp_host, getattr(settings, "SMTP_PORT", 587) or 587, timeout=15) as s:
            try:
                s.starttls()
            except Exception:  # noqa: BLE001 - serveur sans TLS
                pass
            if getattr(settings, "SMTP_USER", None):
                s.login(settings.SMTP_USER, getattr(settings, "SMTP_PASSWORD", ""))
            s.send_message(msg)
        logger.info(f"📧 Email envoyé à {to} : {subject}")
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"⚠️ Envoi email échoué ({to}): {e}")
        return False
