from django.apps import AppConfig


class AdministrationappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "administrationApp"

    def ready(self):
        import administrationApp.signals
