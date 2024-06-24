from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from dashboard.forms import PlaceForm, ReservationForm
from reservations.models import Cuisine, Feature, Place, PlaceType, Reservation
from users.models import CustomUser
from django.utils.text import slugify

@login_required
def places_list(request):
    # Если пользователь является администратором, показываем все заведения
    if request.user.is_staff:
        places = Place.objects.all()
    else:
        # В противном случае показываем только заведения, принадлежащие пользователю
        places = Place.objects.filter(manager=request.user)
    
    context = {
        'places': places,
    }
    return render(request, 'dashboard/places_list.html', context)


@login_required
def reservations_list(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    
    # Проверка, имеет ли пользователь доступ к этому заведению
    if not request.user.is_staff and place.manager != request.user:
        return redirect('places_list')

    reservations = Reservation.objects.filter(place=place).order_by('-created_at')
    
    context = {
        'place': place,
        'reservations': reservations,
    }
    return render(request, 'dashboard/reservations_list.html', context)


@login_required
def all_reservations(request):
    if request.user.is_staff:
        # Администратор видит все бронирования
        reservations = Reservation.objects.all().order_by('-created_at')
    else:
        # Владелец видит только бронирования своих заведений
        user_places = Place.objects.filter(manager=request.user)
        reservations = Reservation.objects.filter(place__in=user_places).order_by('-created_at')

    context = {
        'reservations': reservations,
    }
    return render(request, 'dashboard/all_reservations.html', context)


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    place = reservation.place
    
    # Проверка, имеет ли пользователь доступ к этому бронированию
    if not request.user.is_staff and reservation.place.manager != request.user:
        return HttpResponseForbidden("У вас нет прав на просмотр и редактирование этого бронирования.")

    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            return redirect('dashboard:reservation_detail', reservation_id=reservation.id)
    else:
        form = ReservationForm(instance=reservation)

    context = {
        'reservation': reservation,
        'place': place,
        'form': form
    }
    return render(request, 'dashboard/reservation_detail.html', context)


@login_required
def place_detail(request, slug):
    place = get_object_or_404(Place, slug=slug)
    cuisines = Cuisine.objects.all()
    features = Feature.objects.all()
    
    # Проверяем, что текущий пользователь не является суперпользователем
    # и либо владелец заведения, либо администратором
    if not request.user.is_superuser and not (place.manager == request.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав на редактирование этого заведения.")
    
    if request.method == 'POST':
        form = PlaceForm(request.POST, request.FILES, instance=place)
        if form.is_valid():
            form.save()
            return redirect('dashboard:place_detail', slug=place.slug)
    else:
        form = PlaceForm(instance=place)

    context = {
        'place': place,
        'cuisines': cuisines,
        'features': features,
        'form': form
    }
    return render(request, 'dashboard/place_detail.html', context)