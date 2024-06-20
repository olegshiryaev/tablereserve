from .models import City


def cities(request):
    return {
        'cities': City.objects.all()
    }
