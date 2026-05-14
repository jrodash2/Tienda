import ssl
import certifi
from django.core.mail.backends.smtp import EmailBackend
import logging

logger = logging.getLogger(__name__)

class CustomEmailBackend(EmailBackend):
    def open(self):
        # Crear un contexto SSL que use los certificados de certifi
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        return super().open()

    def send_messages(self, email_messages):
        try:
            result = super().send_messages(email_messages)
            logger.info(f"{result} correos enviados correctamente.")
            return result
        except Exception as e:
            logger.error(f"Error al enviar correos: {e}")
            return 0  # Devolver 0 si no se envían correos
