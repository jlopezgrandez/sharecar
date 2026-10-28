from django.apps import AppConfig


class CarpoolingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'carpooling'
    verbose_name = 'Gestión de Carpooling'

    def ready(self):
        import carpooling.signals
