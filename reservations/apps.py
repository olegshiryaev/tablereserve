from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reservations"
    verbose_name = "Резерв столов"

    def ready(self):
        import reservations.signals
