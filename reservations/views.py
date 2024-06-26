from datetime import date, datetime, timedelta
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import (
    City,
    Cuisine,
    Feature,
    Place,
    PlaceType,
    Reservation,
    Event,
    Discount,
    WorkSchedule,
)
from .forms import ReservationForm, ReviewForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


def main_page(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

    # Получаем популярные заведения, предстоящие события и активные акции для выбранного города
    popular_places = Place.objects.filter(city=city, is_active=True).order_by(
        "-rating"
    )[:5]
    upcoming_events = Event.objects.filter(
        place__city=city, date__gte=date.today(), is_active=True
    ).order_by("date", "start_time")[:5]
    active_discounts = Discount.objects.filter(
        place__city=city, start_date__lte=date.today(), end_date__gte=date.today()
    ).order_by("end_date")[:5]

    # Создаем экземпляр формы для бронирования (предполагая, что ReservationForm определена и имеет атрибут place=None)
    reservation_form = ReservationForm(place=None)

    title = f"Рестораны, кафе и бары {city.name}"

    context = {
        "popular_places": popular_places,
        "upcoming_events": upcoming_events,
        "active_discounts": active_discounts,
        "selected_city": city,
        "form": reservation_form,
        "title": title,
    }

    return render(request, "reservations/main_page.html", context)


def place_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

    # Создаем экземпляр формы для бронирования
    reservation_form = ReservationForm(place=None)

    # Получаем параметры из GET-запроса
    search_query = request.GET.get("search", "")
    sort_by = request.GET.get("sort", "name")  # По умолчанию сортируем по имени
    place_type_filter = request.GET.get("place_type", "")  # Фильтр по типу заведения
    cuisine_filters = request.GET.getlist("cuisine")  # Фильтры по кухням
    min_average_check = request.GET.get(
        "min_average_check", ""
    )  # Минимальный средний чек
    max_average_check = request.GET.get(
        "max_average_check", ""
    )  # Максимальный средний чек
    feature_filters = request.GET.getlist("feature")  # Фильтры по особенностям

    # Фильтрация заведений по городу и поисковому запросу
    places = (
        Place.objects.active()
        .filter(city=city)
        .annotate(
            approved_reviews_count=Count("reviews", filter=Q(reviews__is_approved=True))
        )
    )

    if search_query:
        places = places.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
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
        "name": "name",
        "rating": "-rating",
        "average_check": "average_check",
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
        "places": places,
        "selected_city": city,
        "title": title,
        "total_places": total_places,
        "shown_places": shown_places,
        "sort_by": sort_by,
        "place_types": place_types,
        "cuisines": cuisines,
        "features": features,
        "selected_place_type": place_type_filter,
        "selected_cuisines": cuisine_filters,
        "min_average_check": min_average_check,
        "max_average_check": max_average_check,
        "selected_features": feature_filters,
        "form": reservation_form,
    }
    return render(request, "reservations/place_list.html", context)


def handle_reservation(request, place, form_class, redirect_to):
    if request.method == "POST":
        form = form_class(place, request.POST)  # Pass 'place' as the first argument
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.place = place
            reservation.user = request.user
            reservation.save()
            messages.success(request, "Столик успешно забронирован!")

            # Set session flag to indicate reservation success
            request.session["reservation_successful"] = True

            return reservation
    else:
        form = form_class(place)

    # Сбрасываем сессионный флаг, если он был установлен
    if "reservation_successful" in request.session:
        del request.session["reservation_successful"]

    return form


def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug)
    reservation_form = ReservationForm(place=place)

    if request.method == "POST":
        form = ReservationForm(place, request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.place = place
            reservation.user = request.user
            reservation.save()
            request.session["reservation_successful"] = True
            return HttpResponseRedirect(
                reverse(
                    "place_detail",
                    kwargs={"city_slug": city_slug, "place_slug": place_slug},
                )
            )

    return render(
        request,
        "reservations/place_detail.html",
        {
            "place": place,
            "form": reservation_form,
            "selected_city": city,
        },
    )


def update_time_choices(request, place_id, date):
    # Получаем объект заведения по его ID
    place = Place.objects.get(id=place_id)

    # Преобразуем строковую дату из запроса в объект date
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()

    # Получаем день недели в формате, используемом в модели WorkSchedule
    day_name = selected_date.strftime("%a").upper()

    # Получаем расписание работы заведения для выбранного дня недели
    work_schedule = WorkSchedule.objects.filter(place=place, day=day_name).first()

    # Список для хранения доступных временных слотов
    time_choices = []

    if work_schedule:
        # Определяем время открытия и закрытия заведения
        start_time = work_schedule.open_time
        end_time = (
            datetime.combine(datetime.today(), work_schedule.close_time)
            - timedelta(hours=1)
        ).time()

        # Интервал времени между временными слотами (30 минут)
        interval = timedelta(minutes=30)

        # Определяем текущее время и следующий полуторачасовой интервал
        now = datetime.now()
        current_time = now.time()

        if now.minute < 30:
            next_half_hour = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_half_hour = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )

        # Используем либо начальное время работы, либо следующий полуторачасовой интервал, в зависимости от выбранной даты
        if selected_date == now.date():
            current_time = max(next_half_hour.time(), start_time)
        else:
            current_time = start_time

        # Формируем список доступных временных слотов
        while current_time <= end_time:
            time_choices.append(current_time.strftime("%H:%M"))
            current_time = (
                datetime.combine(datetime.today(), current_time) + interval
            ).time()

    # Возвращаем список временных слотов в формате JSON
    return JsonResponse({"time_choices": time_choices})


def reserve_table(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)
    form = handle_reservation(request, place, ReservationForm, "place_detail")

    context = {
        "place": place,
        "form": form,
        "selected_city": city,
    }

    return render(request, "reservations/place_detail.html", context)


def add_review(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.place = place
            review.user = request.user
            review.save()
            messages.success(request, "Отзыв успешно добавлен.")
            return HttpResponseRedirect(
                reverse("place_detail", args=[city_slug, place_slug])
            )
    else:
        form = ReviewForm()

    return render(
        request,
        "places/add_review.html",
        {"city": city, "selected_city": city, "place": place, "form": form},
    )
