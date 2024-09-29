from django.core.management.base import BaseCommand
from reservations.models import Place, BookingSettings


class Command(BaseCommand):
    help = "Создание BookingSettings для всех существующих заведений"

    def handle(self, *args, **kwargs):
        places = Place.objects.all()
        created_count = 0
        for place in places:
            if not hasattr(place, "bookingsettings"):
                BookingSettings.objects.create(place=place)
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Создано {created_count} объектов BookingSettings.")
        )
