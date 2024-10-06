from datetime import date, datetime, timedelta
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
import calendar
import random
from django.core.exceptions import PermissionDenied

from reservations.utils import calculate_available_time_slots
from users.models import CustomUser, Favorite
from .models import (
    City,
    Cuisine,
    Feature,
    Place,
    PlaceFeature,
    PlaceType,
    Reservation,
    Event,
    Discount,
    Review,
    ReviewResponse,
    WorkSchedule,
)
from .forms import BookingForm, ReservationForm, ReviewForm, ReviewResponseForm
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

    # Получение значения поиска из GET-запроса
    search_query = request.GET.get("search", "")

    # Популярные места
    popular_places = (
        Place.objects.filter(city=city, is_active=True)
        .order_by("-rating")
        .select_related("city")
        .prefetch_related("features", "events")[:9]
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
            place__city=city,
            date__gte=timezone.now().date(),
            is_active=True,
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

    # Случайные последние отзывы (5 штук)
    random_reviews = (
        Review.objects.filter(place__city=city, status="approved")
        .order_by("-id")[:100]  # Сначала берем последние 100 отзывов
        .select_related("user", "place")
    )
    random_reviews = random.sample(
        list(random_reviews), 3
    )  # Затем выбираем случайные 3

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
        "random_reviews": random_reviews,
        "search": search_query,
    }

    return render(request, "reservations/main_page.html", context)


def get_place_word(count):
    """
    Возвращает правильное склонение слова 'заведение' в зависимости от числа.
    """
    # Проверяем исключение для чисел от 11 до 19, которые всегда склоняются как 'заведений'
    if 11 <= count % 100 <= 19:
        return "заведений"

    # Проверяем окончание для чисел, оканчивающихся на 1 (например, 1, 21, 31), кроме исключений
    if count % 10 == 1:
        return "заведение"

    # Проверяем числа, оканчивающиеся на 2, 3, 4 (например, 2, 3, 4, 22, 23, 24)
    if 2 <= count % 10 <= 4:
        return "заведения"

    # Все остальные числа склоняются как 'заведений'
    return "заведений"


def place_list(request, city_slug):
    current_time = timezone.now()
    city = get_object_or_404(City, slug=city_slug)

    # Получаем параметры из GET-запроса
    search_query = request.GET.get("search", "")
    sort_by = request.GET.get("sort", "rating")  # По умолчанию сортируем по имени
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
            approved_reviews_count=Count(
                "reviews", filter=Q(reviews__status="approved")
            )
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
        "name": "name",  # По названию
        "rating": "-rating",  # По рейтингу (от максимального к минимальному)
        "low_to_high": "average_check",  # Сначала недорогие
        "high_to_low": "-average_check",  # Сначала дорогие
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
        .annotate(
            count=Count(
                "places",
                filter=Q(
                    places__is_active=True
                ),  # Подсчитываем только активные заведения
            )
        )
        .filter(count__gt=0)  # Исключаем типы заведений с 0 активными заведениями
        .order_by("-count")
    )

    # Получение доступных кухонь для фильтрации
    cuisines = (
        Cuisine.objects.filter(places__city=city)
        .annotate(
            count=Count(
                "places",
                filter=Q(
                    places__is_active=True
                ),  # Подсчитываем только активные заведения
            )
        )
        .filter(count__gt=0)  # Исключаем кухни с 0 активными заведениями
        .order_by("-count")
    )

    # Получение доступных особенностей для фильтрации
    features = (
        Feature.objects.filter(places__city=city)
        .annotate(
            count=Count(
                "places",
                filter=Q(
                    places__is_active=True
                ),  # Подсчитываем только активные заведения
            )
        )
        .filter(count__gt=0)  # Исключаем особенности с 0 активными заведениями
        .order_by("-count")
    )

    features_on_card = features.filter(place_features__display_on_card=True).distinct()[
        :2
    ]

    # Получение корректной формы слова "место"
    place_word = get_place_word(shown_places)

    # Подготовка данных для отображения особенностей в контексте каждого заведения
    for place in places:
        place.status = place.get_status()
        place.features_list = place.features.all()
        place.features_on_card = place.features.filter(
            place_features__display_on_card=True
        )
        place.review_word = get_review_word(place.approved_reviews_count)

    # Склоняем название города в предложный падеж (например, 'loct')
    city_name = city.name
    city_name_case = inflect_word(city_name, "loct")

    title = f"RESERVE - бронирования столиков в {city_name_case.capitalize()}"

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
    """
    Возвращает правильное склонение слова 'отзыв' в зависимости от числа.
    """
    # Проверяем исключения для чисел от 11 до 14, которые всегда склоняются как 'отзывов'
    if 11 <= count % 100 <= 14:
        return "отзывов"

    # Проверяем окончание для чисел, оканчивающихся на 1 (например, 1, 21, 31), кроме исключений
    if count % 10 == 1:
        return "отзыв"

    # Проверяем числа, оканчивающиеся на 2, 3, 4 (например, 2, 3, 4, 22, 23, 24)
    if 2 <= count % 10 <= 4:
        return "отзыва"

    # Все остальные числа склоняются как 'отзывов'
    return "отзывов"


def get_guest_word(count):
    """
    Возвращает правильное склонение слова 'гость' в зависимости от числа.
    """
    # Проверяем условия для чисел, оканчивающихся на 1, но не на 11
    if count % 10 == 1 and count % 100 != 11:
        return "гостя"

    # Проверяем условия для чисел, оканчивающихся на 2, 3, 4, но не на 12, 13, 14
    if count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return "гостя"

    # Все остальные случаи — 'гостей'
    return "гостей"


def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(
        Place.objects.select_related("city").prefetch_related(
            "images", "work_schedule"
        ),
        slug=place_slug,
    )
    user = request.user

    reservation_form = ReservationForm(place=place, user=user)
    schedules = WorkSchedule.get_sorted_schedules(place.id)

    today_weekday = calendar.day_name[date.today().weekday()].upper()[
        :3
    ]  # Получаем текущий день недели
    today_schedule = next(
        (schedule for schedule in schedules if schedule.day == today_weekday), None
    )

    reviews = (
        place.reviews.filter(status="approved")
        .select_related("user")
        .order_by("-created_at")
    )
    review_count = reviews.count()
    positive_review_count = reviews.filter(rating__gte=4).count()
    negative_review_count = reviews.filter(rating__lt=4).count()
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
                    f"На сегодня в {formatted_time} на {guests_count} {guest_word}."
                )
            elif reservation_date == tomorrow:
                reservation_message = (
                    f"На завтра в {formatted_time} на {guests_count} {guest_word}."
                )
            else:
                reservation_message = f"На {reservation_date.strftime('%d.%m.%Y')} в {formatted_time} на {guests_count} {guest_word}."

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

    # Склоняем название города в предложный падеж (например, 'loct')
    city_name = city.name
    city_name_case = inflect_word(city_name, "loct").capitalize()

    # Формируем заголовок страницы
    place_type = place.type
    place_name = place.name
    place_address = place.address
    title = format_html(
        "Забронировать столик в {} в {}",
        place_name,
        city_name_case,
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
            "positive_review_count": positive_review_count,
            "negative_review_count": negative_review_count,
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
        end_time = work_schedule.close_time

        # Учитываем закрытие после полуночи
        if end_time < start_time:
            end_time = time(23, 59)

        # Получаем интервал времени между временными слотами из BookingSettings
        booking_settings = place.booking_settings
        interval = timedelta(minutes=booking_settings.booking_interval)

        # Получаем недоступный интервал для бронирования от текущего времени
        unavailable_interval = timedelta(minutes=booking_settings.unavailable_interval)

        # Определяем текущее время
        now = datetime.now()

        # Если выбранная дата - сегодня, то вычисляем ближайший доступный временной интервал
        if selected_date == now.date():
            # Рассчитываем ближайшее доступное время с учетом недоступного интервала
            next_available_time = now + unavailable_interval
            current_time = max(next_available_time.time(), start_time)

            # Округляем до ближайшего интервала
            current_time = (
                next_available_time
                + interval
                - timedelta(
                    seconds=next_available_time.second,
                    microseconds=next_available_time.microsecond,
                )
            ).time()

        else:
            # Если дата в будущем, начнем с времени открытия заведения
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
@login_required
def add_review(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)
    review = None

    form = ReviewForm(data=request.POST)
    if form.is_valid():
        # Создаем объект отзыва без сохранения в базу данных
        review = form.save(commit=False)
        review.place = place
        review.user = request.user
        # Сохраняем отзыв в базу данных
        review.save()

        # Добавляем сообщение об успешной отправке отзыва
        messages.success(request, "Ваш отзыв был успешно добавлен.")

        # Перенаправляем на страницу заведения
        return redirect("place_detail", city_slug=city.slug, place_slug=place.slug)

    # Если форма невалидна, оставляем пользователя на той же странице
    return render(
        request,
        "reservations/place_detail.html",
        {
            "city": city,
            "selected_city": city,
            "place": place,
            "form": form,
        },
    )


@login_required
@require_POST
def add_review_response(request, city_slug, place_slug, review_id):
    review = get_object_or_404(Review, id=review_id)
    place = get_object_or_404(Place, slug=place_slug)

    if request.method == "POST":
        response_text = request.POST.get("response_text")
        if response_text:
            response = ReviewResponse.objects.create(
                review=review,
                place=place,
                user=request.user,  # пользователь, оставляющий ответ
                text=response_text,
            )
            return redirect(
                "place_detail", city_slug=city_slug, place_slug=place_slug
            )  # Перенаправление на страницу места
    return render(request, "add_review_response.html", {"review": review})


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


def check_open_status(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    selected_date = request.GET.get("date")

    if selected_date:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d")
        selected_weekday = calendar.day_name[
            selected_date.weekday()
        ]  # Получаем день недели (например, 'Monday')

        # Проверяем, работает ли заведение в этот день недели
        is_open = place.work_schedule.filter(
            day=selected_weekday, is_closed=False
        ).exists()

        return JsonResponse({"is_open": is_open})

    return JsonResponse({"error": "Invalid date"}, status=400)


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
