from .models import City, Place, Reservation


def cities(request):
    return {"cities": City.objects.all()}


def selected_city(request):
    city_slug = request.session.get("selected_city", "arh")
    city = City.objects.filter(slug=city_slug).first()
    return {"selected_city": city}


def pending_reservations_count(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            pending_count = Reservation.objects.filter(status="pending").count()
        else:
            user_places = Place.objects.filter(manager=request.user)
            pending_count = Reservation.objects.filter(
                place__in=user_places, status="pending"
            ).count()
    else:
        pending_count = 0  # Для неавторизованных пользователей

    return {"pending_reservations_count": pending_count}
