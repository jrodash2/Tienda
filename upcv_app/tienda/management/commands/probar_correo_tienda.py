from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Prueba el envío de correo SMTP de la tienda"

    def add_arguments(self, parser):
        parser.add_argument(
            "email",
            type=str,
            help="Correo destino para enviar la prueba"
        )

    def handle(self, *args, **options):
        email_destino = options["email"]

        self.stdout.write(
            f"Probando envío de correo a: {email_destino}"
        )

        self.stdout.write(
            f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NO CONFIGURADO')}"
        )
        self.stdout.write(
            f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NO CONFIGURADO')}"
        )

        try:
            resultado = send_mail(
                subject="Prueba de correo desde Django",
                message=(
                    "Este es un correo de prueba enviado desde Django "
                    "para validar la configuración SMTP de la tienda."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[email_destino],
                fail_silently=False,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Correo enviado correctamente. Resultado: {resultado}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    "Error enviando correo SMTP:"
                )
            )
            self.stdout.write(
                self.style.ERROR(str(e))
            )
            raise
