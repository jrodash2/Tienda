from django.apps import AppConfig

class AlmacenAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'almacen_app'

    def ready(self):
        import almacen_app.signals  # 👈 importa tus signals aquí
