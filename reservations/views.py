from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import City, Cuisine, Feature, Place, PlaceType, Reservation
from .forms import ReservationForm, ReviewForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q


def place_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

    # Создаем экземпляр формы для бронирования
    reservation_form = ReservationForm(place=None)

    # Получаем параметры из GET-запроса
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')  # По умолчанию сортируем по имени
    place_type_filter = request.GET.get('place_type', '')  # Фильтр по типу заведения
    cuisine_filters = request.GET.getlist('cuisine')  # Фильтры по кухням
    min_average_check = request.GET.get('min_average_check', '')  # Минимальный средний чек
    max_average_check = request.GET.get('max_average_check', '')  # Максимальный средний чек
    feature_filters = request.GET.getlist('feature')  # Фильтры по особенностям

    # Фильтрация заведений по городу и поисковому запросу
    places = Place.objects.active().filter(city=city).annotate(
        approved_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )

    if search_query:
        places = places.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Фильтрация по типу заведения
    if place_type_filter:
        place_type = get_object_or_404(PlaceType, slug=place_type_filter)
        places = places.filter(type=place_type)

    # Фильтрация по кухням
    if cuisine_filters:
        cuisines = Cuisine.objects.filter(slug__in=cuisine_filters)
        places = places.filter(cuisines__in=cuisines).distinct()

    # Фильтрация по диапазону среднего чека
    if min_average_check:
        places = places.filter(average_check__gte=min_average_check)
    if max_average_check:
        places = places.filter(average_check__lte=max_average_check)

    # Фильтрация по особенностям
    if feature_filters:
        features = Feature.objects.filter(id__in=feature_filters)
        places = places.filter(features__in=features).distinct()

    # Сортировка заведений
    sort_options = {
        'name': 'name',
        'rating': '-rating',
        'average_check': 'average_check',
    }
    if sort_by in sort_options:
        places = places.order_by(sort_options[sort_by])

    # Получение общего количества и количества показанных заведений
    total_places = places.count()
    shown_places = places.count()

    # Получение доступных типов заведений для фильтрации
    place_types = PlaceType.objects.all()

    # Получение доступных кухонь для фильтрации
    cuisines = Cuisine.objects.all()

    # Получение доступных особенностей для фильтрации
    features = Feature.objects.all()

    title = f"Рестораны, кафе и бары {city.name}а"

    context = {
        'places': places,
        'selected_city': city,
        'title': title,
        'total_places': total_places,
        'shown_places': shown_places,
        'sort_by': sort_by,
        'place_types': place_types,
        'cuisines': cuisines,
        'features': features,
        'selected_place_type': place_type_filter,
        'selected_cuisines': cuisine_filters,
        'min_average_check': min_average_check,
        'max_average_check': max_average_check,
        'selected_features': feature_filters,
        'form': reservation_form,
    }
    return render(request, 'reservations/place_list.html', context)


def handle_reservation(request, place, form_class, redirect_to):
    if request.method == 'POST':
        form = form_class(place, request.POST)  # Pass 'place' as the first argument
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.place = place
            reservation.user = request.user
            reservation.save()
            messages.success(request, 'Столик успешно забронирован!')

            # Set session flag to indicate reservation success
            request.session['reservation_successful'] = True

            return reservation
    else:
        form = form_class(place)

    # Сбрасываем сессионный флаг, если он был установлен
    if 'reservation_successful' in request.session:
        del request.session['reservation_successful']

    return form


@login_required
def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)
    form = handle_reservation(request, place, ReservationForm, 'place_detail')

    title = f"{place.type} {place.name}, {place.address}"

    context = {
        'place': place,
        'form': form,
        'selected_city': city,
        'title': title,
    }
    return render(request, 'reservations/place_detail.html', context)


@login_required
def reserve_table(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)
    form = handle_reservation(request, place, ReservationForm, 'place_detail')

    context = {
        'place': place,
        'form': form,
        'selected_city': city,
    }

    return render(request, 'reservations/place_detail.html', context)


def add_review(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.place = place
            review.user = request.user
            review.save()
            messages.success(request, 'Отзыв успешно добавлен.')
            return HttpResponseRedirect(reverse('place_detail', args=[city_slug, place_slug]))
    else:
        form = ReviewForm()

    return render(request, 'places/add_review.html',
                  {'city': city, 'selected_city': city, 'place': place, 'form': form})
