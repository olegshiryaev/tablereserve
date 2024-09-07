from datetime import date, datetime, timedelta
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
import calendar

from reservations.utils import calculate_available_time_slots
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
from .forms import BookingForm, ReservationForm, ReviewForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.html import format_html
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .utils import inflect_word

User = get_user_model()


def main_page(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)
    city_name_genitive = inflect_word(city.name, "gent")
    city_name_locative = inflect_word(city.name, "loct")

    # Популярные места
    popular_places = (
        Place.objects.filter(city=city, is_active=True)
        .order_by("-rating")
        .prefetch_related("features")[:9]
    )
    total_places_count = Place.objects.filter(city=city, is_active=True).count()

    # Любимые места пользователя
    favorite_places = []
    if request.user.is_authenticated:
        favorite_places = Favorite.objects.filter(user=request.user).values_list(
            "place_id", flat=True
        )

    # Предстоящие события
    upcoming_events = (
        Event.objects.filter(
            place__city=city, date__gte=timezone.now().date(), is_active=True
        )
        .order_by("date", "start_time")
        .select_related("place")[:5]
    )

    # Активные скидки
    active_discounts = (
        Discount.objects.filter(
            place__city=city,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        )
        .order_by("end_date")
        .select_related("place")[:5]
    )

    # Особенности на карточках
    features_on_card = Feature.objects.filter(
        place_features__display_on_card=True
    ).distinct()[:2]

    # Добавляем особенности к заведениям
    for place in popular_places:
        place.features_on_card = place.features.filter(
            place_features__display_on_card=True
        )

    # Заголовок страницы
    title = f"Рестораны, кафе и бары {city_name_genitive.capitalize()}"

    # Контекст для шаблона
    context = {
        "popular_places": popular_places,
        "upcoming_events": upcoming_events,
        "active_discounts": active_discounts,
        "selected_city": city,
        "title": title,
        "favorite_places": favorite_places,
        "total_places_count": total_places_count,
        "features_on_card": features_on_card,
        "city_name_locative": city_name_locative,
    }

    return render(request, "reservations/main_page.html", context)


def get_place_word(count):
    if 11 <= count % 100 <= 19:
        return "заведений"
    elif count % 10 == 1:
        return "заведение"
    elif 2 <= count % 10 <= 4:
        return "заведения"
    else:
        return "заведений"


def place_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)

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

    # Пагинация
    per_page = 18  # Количество заведений на странице
    paginator = Paginator(places, per_page)
    page = request.GET.get("page", 1)

    try:
        places = paginator.page(page)
    except PageNotAnInteger:
        places = paginator.page(1)
    except EmptyPage:
        places = paginator.page(paginator.num_pages)

    # Получение общего количества и количества показанных заведений
    total_places = paginator.count
    shown_places = len(places)

    # Получение доступных типов заведений для фильтрации
    place_types = (
        PlaceType.objects.filter(places__city=city)
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .filter(count__gt=0)  # Исключаем типы заведений с 0 заведениями
        .order_by("-count")
    )

    # Получение доступных кухонь для фильтрации
    cuisines = (
        Cuisine.objects.filter(places__city=city)
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .filter(count__gt=0)  # Исключаем кухни с 0 заведениями
        .order_by("-count")
    )

    # Получение доступных особенностей для фильтрации
    features = (
        Feature.objects.filter(places__city=city)
        .annotate(count=Count("places", filter=Q(places__city=city)))
        .filter(count__gt=0)  # Исключаем особенности с 0 заведениями
        .order_by("-count")
    )

    features_on_card = features.filter(place_features__display_on_card=True).distinct()[
        :2
    ]

    # Получение корректной формы слова "место"
    place_word = get_place_word(shown_places)

    # Подготовка данных для отображения особенностей в контексте каждого заведения
    for place in places:
        place.features_on_card = place.features.filter(
            place_features__display_on_card=True
        )

    # Склоняем название города в предложный падеж (например, 'loct')
    city_name = city.name
    city_name_case = inflect_word(city_name, "loct")

    title = f"Поиск мест в {city_name_case.capitalize()} | Reserve.cafe"

    context = {
        "features_on_card": features_on_card,
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
        "favorite_places": favorite_places,
        "paginator": paginator,  # Добавляем paginator в контекст
    }
    return render(request, "reservations/place_list.html", context)


def handle_reservation(request, place, form_class):
    form = form_class(place, request.POST or None)
    user_name = None
    reservation_data = None

    if request.method == "POST" and form.is_valid():
        reservation = form.save(commit=False)
        reservation.place = place
        reservation.user = request.user if request.user.is_authenticated else None
        reservation.save()

        # Подготовка данных для модального окна
        user_name = (
            request.user.get_full_name() if request.user.is_authenticated else "Гость"
        )
        reservation_data = {
            "date": reservation.date.strftime("%d-%m-%Y"),
            "time": reservation.time.strftime("%H:%M"),
            "guests": reservation.guests,
            "phone": reservation.customer_phone,
        }

    print("User Name:", user_name)  # Debugging line
    print("Reservation Data:", reservation_data)  # Debugging line

    return form, user_name, reservation_data


def get_review_word(count):
    if count % 100 in [11, 12, 13, 14]:
        return "отзывов"
    elif count % 10 == 1:
        return "отзыв"
    elif 2 <= count % 10 <= 4:
        return "отзыва"
    else:
        return "отзывов"


def get_guest_word(count):
    if count % 10 == 1 and count % 100 != 11:
        return "гостя"
    elif count % 10 in [2, 3, 4] and not count % 100 in [12, 13, 14]:
        return "гостя"
    else:
        return "гостей"


def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug)
    user = request.user

    reservation_form = ReservationForm(place=place, user=user)
    schedules = WorkSchedule.get_sorted_schedules(place.id)

    today_weekday = calendar.day_name[date.today().weekday()].upper()[
        :3
    ]  # Получаем текущий день недели
    today_schedule = next(
        (schedule for schedule in schedules if schedule.day == today_weekday), None
    )

    reviews = place.reviews.filter(is_approved=True)
    review_count = reviews.count()
    average_rating = place.rating

    # Получаем особенности заведения вместе с описаниями
    place_features = place.get_place_features()

    # Инициализация переменных для модального окна
    reservation_successful = False
    reservation_data = None
    reservation_message = None

    if request.method == "POST":
        reservation_form = ReservationForm(place, request.POST, user=user)
        if reservation_form.is_valid():
            reservation = reservation_form.save(commit=False)
            reservation.place = place
            reservation.user = user if user.is_authenticated else None
            reservation.save()
            reservation_successful = True

            # Форматирование даты
            today = date.today()
            tomorrow = today + timedelta(days=1)
            reservation_date = reservation.date
            formatted_time = reservation.time.strftime("%H:%M")
            guests_count = reservation.guests
            guest_word = get_guest_word(guests_count)

            if reservation_date == today:
                reservation_message = (
                    f"сегодня в {formatted_time} на {guests_count} {guest_word}."
                )
            elif reservation_date == tomorrow:
                reservation_message = (
                    f"завтра в {formatted_time} на {guests_count} {guest_word}."
                )
            else:
                reservation_message = f"{format(reservation_date, 'd.m.Y')} в {formatted_time} на {guests_count} {guest_word}."

            reservation_data = {
                "name": reservation.customer_name,
                "date": reservation.date,
                "time": reservation.time,
                "guests": guests_count,
                "phone": reservation.customer_phone,
            }

    # Проверка, добавлено ли заведение в избранное текущим пользователем
    is_favorited = False
    if request.user.is_authenticated:
        if Favorite.objects.filter(user=request.user, place=place).exists():
            is_favorited = True

    # Получение корректной формы слова "отзыв"
    review_word = get_review_word(reviews.count())

    # Получаем похожие заведения
    similar_places = place.get_similar_places()

    # Получение данных о залах и столиках
    halls = place.halls.all()

    # Склоняем тип заведения в предложный падеж
    place_type_str = str(place.type) if place.type else "Тип заведения не указан"
    place_type_phrase = inflect_word(place_type_str, "loct")

    # Формируем заголовок страницы
    place_type = place.type
    place_name = place.name
    place_address = place.address
    title = format_html(
        "{} {}, {}: меню, фото, отзывы | Reserve.cafe",
        place_type,
        place_name,
        place_address,
    )

    return render(
        request,
        "reservations/place_detail.html",
        {
            "place": place,
            "place_type_phrase": place_type_phrase,
            "reservation_form": reservation_form,
            "selected_city": city,
            "schedules": schedules,
            "today_weekday": today_weekday,
            "today_schedule": today_schedule,
            "average_rating": average_rating,
            "reviews": reviews,
            "review_count": review_count,
            "review_word": review_word,
            "is_favorited": is_favorited,
            "similar_places": similar_places,
            "reservation_successful": reservation_successful,
            "reservation_data": reservation_data,
            "reservation_message": reservation_message,
            "place_features": place_features,
            "halls": halls,
            "title": title,
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

    form, user_name, reservation_data = handle_reservation(
        request, place, ReservationForm
    )

    context = {
        "place": place,
        "form": form,
        "selected_city": city,
        "user_name": user_name,
        "reservation_data": reservation_data,
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


# def place_detail(request, city_slug, place_slug):
#     city = get_object_or_404(City, slug=city_slug)
#     place = get_object_or_404(Place, slug=place_slug, city=city)
#     today_date = timezone.now().date().strftime("%Y-%m-%d")  # Используем timezone

#     return render(
#         request,
#         "reservations/place_detail.html",
#         {
#             "place": place,
#             "today_date": today_date,
#             "selected_city": city,
#         },
#     )


def get_available_time_slots(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    selected_date_str = request.GET.get("date")

    if selected_date_str:
        try:
            selected_date = timezone.datetime.strptime(
                selected_date_str, "%Y-%m-%d"
            ).date()
            time_slots = calculate_available_time_slots(place, selected_date)
            return JsonResponse(time_slots, safe=False)
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)

    return JsonResponse([], safe=False)


def create_booking(request, place_id):
    place = get_object_or_404(Place, id=place_id)

    if request.method == "POST":
        form = BookingForm(place, request.POST)
        if form.is_valid():
            booking_date = form.cleaned_data["booking_date"]
            booking_time = form.cleaned_data["booking_time"]

            try:
                booking_datetime = timezone.make_aware(
                    datetime.datetime.combine(
                        booking_date,
                        datetime.datetime.strptime(booking_time, "%H:%M").time(),
                    )
                )
            except ValueError:
                return render(
                    request,
                    "reservations/place_detail.html",
                    {
                        "place": place,
                        "form": form,
                        "today_date": timezone.now().date().strftime("%Y-%m-%d"),
                        "error": "Invalid time format",
                    },
                )

            if place.is_open_for_booking(booking_datetime):
                Booking.objects.create(
                    place=place,
                    user=request.user,
                    booking_time=booking_datetime,
                    guests_count=form.cleaned_data["guests_count"],
                )
                return redirect("success_page")
            else:
                form.add_error(None, "The place is not available at the selected time.")

    else:
        form = BookingForm(place)

    return render(
        request,
        "reservations/place_detail.html",
        {
            "place": place,
            "form": form,
            "today_date": timezone.now().date().strftime("%Y-%m-%d"),
        },
    )
