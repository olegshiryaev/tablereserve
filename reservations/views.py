from datetime import date, datetime, timedelta
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from users.models import CustomUser, Favorite
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
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()


def main_page(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

    # Популярные места, предстоящие события и активные скидки для выбранного города
    popular_places = Place.objects.filter(city=city, is_active=True).order_by(
        "-rating"
    )[:9]
    total_places_count = Place.objects.filter(city=city, is_active=True).count()

    if request.user.is_authenticated:
        favorite_places = Favorite.objects.filter(user=request.user).values_list(
            "place_id", flat=True
        )
    else:
        favorite_places = []
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
        "favorite_places": favorite_places,
        "total_places_count": total_places_count,
    }

    return render(request, "reservations/main_page.html", context)


def get_place_word(count):
    if 11 <= count % 100 <= 19:
        return "мест"
    elif count % 10 == 1:
        return "место"
    elif 2 <= count % 10 <= 4:
        return "места"
    else:
        return "мест"


def place_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

    # Создаем экземпляр формы для бронирования
    reservation_form = ReservationForm(place=None)

    # Получаем параметры из GET-запроса
    search_query = request.GET.get("search", "")
    sort_by = request.GET.get("sort", "name")  # По умолчанию сортируем по имени
    place_type_filters = request.GET.getlist("place_type")  # Фильтр по типу заведения
    cuisine_filters = request.GET.getlist("cuisine")  # Фильтры по кухням
    average_check_filters = request.GET.getlist(
        "average_check"
    )  # Фильтры по среднему чеку
    feature_filters = request.GET.getlist("feature")  # Фильтры по особенностям
    rating_filter = request.GET.get("rating", "")  # Фильтр по рейтингу

    # Фильтрация заведений по городу и поисковому запросу
    places = (
        Place.objects.active()
        .filter(city=city)
        .annotate(
            approved_reviews_count=Count("reviews", filter=Q(reviews__is_approved=True))
        )
        .select_related("type")  # Загрузка связанных данных о типе заведения
    )
    if request.user.is_authenticated:
        favorite_places = Favorite.objects.filter(user=request.user).values_list(
            "place_id", flat=True
        )
    else:
        favorite_places = []

    if search_query:
        places = places.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    # Фильтрация по типу заведения
    if place_type_filters:
        places = places.filter(type__slug__in=place_type_filters).distinct()

    # Фильтрация по кухням
    if cuisine_filters:
        cuisines = Cuisine.objects.filter(slug__in=cuisine_filters)
        places = places.filter(cuisines__in=cuisines).distinct()

    # Фильтрация по диапазону среднего чека
    if average_check_filters:
        average_check_conditions = Q()
        for check in average_check_filters:
            if check == "<500":
                average_check_conditions |= Q(average_check__lt=500)
            elif check == "500-1000":
                average_check_conditions |= Q(
                    average_check__gte=500, average_check__lte=1000
                )
            elif check == "1000-1500":
                average_check_conditions |= Q(
                    average_check__gte=1000, average_check__lte=1500
                )
            elif check == "1500-2000":
                average_check_conditions |= Q(
                    average_check__gte=1500, average_check__lte=2000
                )
            elif check == ">2000":
                average_check_conditions |= Q(average_check__gt=2000)
        places = places.filter(average_check_conditions)

    # Фильтрация по особенностям
    if feature_filters:
        features = Feature.objects.filter(id__in=feature_filters)
        places = places.filter(features__in=features).distinct()

    # Фильтрация по рейтингу
    if rating_filter:
        places = places.filter(rating__gte=rating_filter)

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
    place_types = (
        PlaceType.objects.all()
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .order_by("-count")
    )

    # Получение доступных кухонь для фильтрации
    cuisines = (
        Cuisine.objects.all()
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .order_by("-count")
    )

    # Получение доступных особенностей для фильтрации
    features = (
        Feature.objects.all()
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .order_by("-count")
    )

    # Получение корректной формы слова "место"
    place_word = get_place_word(shown_places)

    title = f"Рестораны, кафе и бары {city.name}а"

    context = {
        "places": places,
        "selected_city": city,
        "title": title,
        "total_places": total_places,
        "shown_places": shown_places,
        "place_word": place_word,
        "sort_by": sort_by,
        "place_types": place_types,
        "cuisines": cuisines,
        "features": features,
        "selected_place_types": place_type_filters,
        "selected_cuisines": cuisine_filters,
        "selected_average_checks": average_check_filters,
        "selected_features": feature_filters,
        "selected_rating": rating_filter,
        "form": reservation_form,
        "favorite_places": favorite_places,
    }
    return render(request, "reservations/place_list.html", context)


def handle_reservation(request, place, form_class, redirect_to):
    if request.method == "POST":
        form = form_class(place, request.POST)  # Pass 'place' as the first argument
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.place = place
            reservation.user = request.user if request.user.is_authenticated else None
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


def get_review_word(count):
    if count % 100 in [11, 12, 13, 14]:
        return "отзывов"
    elif count % 10 == 1:
        return "отзыв"
    elif 2 <= count % 10 <= 4:
        return "отзыва"
    else:
        return "отзывов"


def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug)
    reservation_form = ReservationForm(place=place)
    schedules = WorkSchedule.get_sorted_schedules(place.id)
    reviews = place.reviews.filter(is_approved=True)

    if request.method == "POST":
        reservation_form = ReservationForm(place, request.POST)
        if reservation_form.is_valid():
            reservation = reservation_form.save(commit=False)
            reservation.place = place
            reservation.user = request.user if request.user.is_authenticated else None
            reservation.save()
            request.session["reservation_successful"] = True
            return HttpResponseRedirect(
                reverse(
                    "place_detail",
                    kwargs={"city_slug": city_slug, "place_slug": place_slug},
                )
            )

    # Проверка, добавлено ли заведение в избранное текущим пользователем
    is_favorited = False
    if request.user.is_authenticated:
        if Favorite.objects.filter(user=request.user, place=place).exists():
            is_favorited = True

    # Получение корректной формы слова "отзыв"
    review_word = get_review_word(reviews.count())

    return render(
        request,
        "reservations/place_detail.html",
        {
            "place": place,
            "reservation_form": reservation_form,
            "selected_city": city,
            "schedules": schedules,
            "reviews": reviews,
            "review_word": review_word,
            "is_favorited": is_favorited,
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


@require_POST
def add_review(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)
    review = None

    # A comment was posted
    form = ReviewForm(data=request.POST)
    if form.is_valid():
        # Create a Comment object without saving it to the database
        review = form.save(commit=False)
        # Assign the post to the comment
        review.place = place
        review.user = request.user
        # Save the comment to the database
        review.save()
    return render(
        request,
        "reservations/place_detail.html",
        {
            "city": city,
            "selected_city": city,
            "place": place,
            "form": form,
            "review": review,
        },
    )
