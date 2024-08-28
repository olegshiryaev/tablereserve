from .models import City


def cities(request):
    return {"cities": City.objects.all()}


def selected_city(request):
    city_slug = request.session.get("selected_city", "arh")
    city = City.objects.filter(slug=city_slug).first()
    return {"selected_city": city}
