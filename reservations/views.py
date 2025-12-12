from datetime import date, datetime, timedelta, time
import calendar
import random

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Q

from .models import (
    Cuisine, Feature, Place, PlaceType, Reservation,
    Event, Discount, Review, ReviewResponse, WorkSchedule, Favorite
)
from .forms import ReservationForm, ReviewForm, ReviewResponseForm
from .utils import calculate_available_time_slots
from locations.models import City
from django.contrib.auth import get_user_model

User = get_user_model()


# Словари для склонений (пример, можно расширить)
CITY_CASES = {
    "Москва": {"gent": "Москвы", "loct": "Москве"},
    "Санкт-Петербург": {"gent": "Санкт-Петербурга", "loct": "Санкт-Петербурге"},
}

PLACE_TYPE_CASES = {
    "Ресторан": {"loct": "ресторане"},
    "Кафе": {"loct": "кафе"},
    "Бар": {"loct": "баре"},
}


def get_word_form(count, forms=("заведение", "заведения", "заведений")):
    if 11 <= count % 100 <= 19:
        return forms[2]
    elif count % 10 == 1:
        return forms[0]
    elif 2 <= count % 10 <= 4:
        return forms[1]
    else:
        return forms[2]


def get_place_word(count):
    return get_word_form(count, ("заведение", "заведения", "заведений"))


def get_review_word(count):
    return get_word_form(count, ("отзыв", "отзыва", "отзывов"))


def get_guest_word(count):
    return get_word_form(count, ("гость", "гостя", "гостей"))


def inflect_city(city_name, case="loct"):
    return CITY_CASES.get(city_name, {}).get(case, city_name)


def inflect_place_type(place_type, case="loct"):
    return PLACE_TYPE_CASES.get(str(place_type), {}).get(case, str(place_type))


# ---------------- Main Pages ----------------

def get_recommended_places(user, limit=None):
    if user.is_authenticated:
        recommended = Place.objects.recommended_places(user)
        return recommended[:limit] if limit else recommended
    return Place.objects.none()


def main_page(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)
    city_name_genitive = inflect_city(city.name, "gent")
    city_name_locative = inflect_city(city.name, "loct")

    search_query = request.GET.get("search", "")

    popular_places = (
        Place.objects.filter(city=city, is_active=True)
        .order_by("-rating")
        .select_related("city")
        .prefetch_related("features", "events")[:9]
    )
    total_places_count = Place.objects.filter(city=city, is_active=True).count()

    favorite_places = []
    if request.user.is_authenticated:
        favorite_places = Favorite.objects.filter(user=request.user).values_list(
            "place_id", flat=True
        )

    upcoming_events = (
        Event.objects.filter(
            place__city=city,
            date__gte=timezone.now().date(),
            is_active=True,
        )
        .order_by("date", "start_time")
        .select_related("place")[:5]
    )

    active_discounts = (
        Discount.objects.filter(
            place__city=city,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        )
        .order_by("end_date")
        .select_related("place")[:5]
    )

    reviews = Review.objects.filter(place__city=city, status="approved").order_by("-created_at")[:100]
    random_reviews = random.sample(list(reviews), min(len(reviews), 3)) if reviews else []

    recommended_places = get_recommended_places(request.user, limit=3)

    title = f"Рестораны, кафе и бары {city_name_genitive.capitalize()}"

    context = {
        "popular_places": popular_places,
        "upcoming_events": upcoming_events,
        "active_discounts": active_discounts,
        "selected_city": city,
        "title": title,
        "favorite_places": favorite_places,
        "total_places_count": total_places_count,
        "city_name_locative": city_name_locative,
        "random_reviews": random_reviews,
        "search": search_query,
        "recommended_places": recommended_places,
    }
    return render(request, "reservations/main_page.html", context)


# ---------------- Place List & Detail ----------------

def place_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)
    search_query = request.GET.get("search", "")
    sort_by = request.GET.get("sort", "rating")
    place_type_filters = request.GET.getlist("place_type")
    cuisine_filters = request.GET.getlist("cuisine")
    average_check_filters = request.GET.getlist("average_check")
    feature_filters = request.GET.getlist("feature")
    rating_filter = request.GET.get("rating", "")

    places = (
        Place.objects.active()
        .filter(city=city)
        .annotate(approved_reviews_count=Count("reviews", filter=Q(reviews__status="approved")))
        .select_related("type")
    )

    favorite_places = []
    if request.user.is_authenticated:
        favorite_places = Favorite.objects.filter(user=request.user).values_list("place_id", flat=True)

    if search_query:
        places = places.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    # Filters
    if place_type_filters:
        places = places.filter(type__slug__in=place_type_filters).distinct()
    if cuisine_filters:
        cuisines = Cuisine.objects.filter(slug__in=cuisine_filters)
        places = places.filter(cuisines__in=cuisines).distinct()
    if average_check_filters:
        q_avg = Q()
        for check in average_check_filters:
            if check == "<500":
                q_avg |= Q(average_check__lt=500)
            elif check == "500-1000":
                q_avg |= Q(average_check__gte=500, average_check__lte=1000)
            elif check == "1000-1500":
                q_avg |= Q(average_check__gte=1000, average_check__lte=1500)
            elif check == "1500-2000":
                q_avg |= Q(average_check__gte=1500, average_check__lte=2000)
            elif check == ">2000":
                q_avg |= Q(average_check__gt=2000)
        places = places.filter(q_avg)
    if feature_filters:
        features = Feature.objects.filter(id__in=feature_filters)
        places = places.filter(features__in=features).distinct()
    if rating_filter:
        places = places.filter(rating__gte=rating_filter)

    # Sorting
    sort_options = {
        "name": "name",
        "rating": "-rating",
        "low_to_high": "average_check",
        "high_to_low": "-average_check",
    }
    if sort_by in sort_options:
        places = places.order_by(sort_options[sort_by])

    # Pagination
    paginator = Paginator(places, 18)
    page = request.GET.get("page", 1)
    try:
        places = paginator.page(page)
    except PageNotAnInteger:
        places = paginator.page(1)
    except EmptyPage:
        places = paginator.page(paginator.num_pages)

    total_places = paginator.count
    shown_places = len(places)
    place_word = get_place_word(shown_places)

    # Features for cards
    features = Feature.objects.filter(places__city=city).distinct()
    features_on_card = features.filter(place_features__display_on_card=True)[:2]

    # Context
    for place in places:
        place.status = place.get_status()
        place.features_list = place.features.all()
        place.features_on_card = place.features.filter(place_features__display_on_card=True)
        place.review_word = get_review_word(place.approved_reviews_count)

    city_name_case = inflect_city(city.name, "loct")
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
        "place_types": PlaceType.objects.all(),
        "cuisines": Cuisine.objects.all(),
        "features": features,
        "selected_place_types": place_type_filters,
        "selected_cuisines": cuisine_filters,
        "selected_average_checks": average_check_filters,
        "selected_features": feature_filters,
        "selected_rating": rating_filter,
        "favorite_places": favorite_places,
        "paginator": paginator,
    }
    return render(request, "reservations/place_list.html", context)


def place_detail(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place.objects.select_related("city").prefetch_related("images", "work_schedule"), slug=place_slug)

    user = request.user
    can_leave_review = False
    if user.is_authenticated:
        yesterday = timezone.now() - timedelta(days=1)
        can_leave_review = user.reservations.filter(place=place, status='confirmed', date__gte=yesterday.date()).exists()

    reservation_form = ReservationForm(place=place, user=user)
    schedules = WorkSchedule.get_sorted_schedules(place.id)
    today_weekday = calendar.day_name[date.today().weekday()].upper()[:3]
    today_schedule = next((s for s in schedules if s.day == today_weekday), None)

    reviews = place.reviews.filter(status="approved").select_related("user").order_by("-created_at")
    review_count = reviews.count()
    review_word = get_review_word(review_count)

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

            reservation_date = reservation.date
            formatted_time = reservation.time.strftime("%H:%M")
            guests_count = reservation.guests
            guest_word = get_guest_word(guests_count)

            if reservation_date == date.today():
                reservation_message = f"На сегодня в {formatted_time} на {guests_count} {guest_word}."
            elif reservation_date == date.today() + timedelta(days=1):
                reservation_message = f"На завтра в {formatted_time} на {guests_count} {guest_word}."
            else:
                reservation_message = f"На {reservation_date.strftime('%d.%m.%Y')} в {formatted_time} на {guests_count} {guest_word}."

            reservation_data = {
                "name": reservation.customer_name,
                "date": reservation.date,
                "time": reservation.time,
                "guests": guests_count,
                "phone": reservation.customer_phone,
            }

    is_favorited = False
    if user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=user, place=place).exists()

    place_type_phrase = inflect_place_type(place.type, "loct")
    city_name_case = inflect_city(city.name, "loct").capitalize()

    title = f"Забронировать столик в {place.name} в {city_name_case}"

    context = {
        "place": place,
        "place_type_phrase": place_type_phrase,
        "reservation_form": reservation_form,
        "can_leave_review": can_leave_review,
        "selected_city": city,
        "schedules": schedules,
        "today_weekday": today_weekday,
        "today_schedule": today_schedule,
        "reviews": reviews,
        "review_count": review_count,
        "review_word": review_word,
        "is_favorited": is_favorited,
        "reservation_successful": reservation_successful,
        "reservation_data": reservation_data,
        "reservation_message": reservation_message,
    }

    return render(request, "reservations/place_detail.html", context)


# ---------------- JSON API ----------------

def get_available_time_slots(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse([], safe=False)
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        slots = calculate_available_time_slots(place, selected_date)
        return JsonResponse(slots, safe=False)
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)



# ---------------- Reviews ----------------

@login_required
def add_review(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)

    # Проверка подтвержденного бронирования за последние 24 часа
    yesterday = timezone.now() - timedelta(days=1)
    if not request.user.reservations.filter(place=place, status="confirmed", date__gte=yesterday.date()).exists():
        messages.error(request, "Вы не можете оставить отзыв без подтвержденного бронирования за последние 24 часа")
        return redirect("place_detail", city_slug=city.slug, place_slug=place.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.place = place
            review.user = request.user
            review.save()
            messages.success(request, "Ваш отзыв успешно добавлен")
            return redirect("place_detail", city_slug=city.slug, place_slug=place.slug)
        else:
            messages.error(request, "Произошла ошибка при добавлении отзыва")

    else:
        form = ReviewForm()

    return render(request, "reservations/place_detail.html", {
        "place": place,
        "form": form,
        "selected_city": city,
    })


@login_required
def add_review_response(request, city_slug, place_slug, review_id):
    review = get_object_or_404(Review, id=review_id)
    place = get_object_or_404(Place, slug=place_slug)

    if request.method == "POST":
        response_text = request.POST.get("response_text")
        if response_text:
            ReviewResponse.objects.create(
                review=review,
                place=place,
                user=request.user,
                text=response_text
            )
            messages.success(request, "Ответ успешно добавлен")
            return redirect("place_detail", city_slug=city_slug, place_slug=place_slug)

    return render(request, "reservations/add_review_response.html", {"review": review})


# ---------------- Reservation ----------------

def handle_reservation(request, place):
    """Унифицированная функция обработки бронирования"""
    form = ReservationForm(place=place, user=request.user, data=request.POST or None)
    reservation_data = None
    reservation_message = None
    success = False

    if request.method == "POST" and form.is_valid():
        reservation = form.save(commit=False)
        reservation.place = place
        reservation.user = request.user if request.user.is_authenticated else None
        reservation.save()
        success = True

        guests_count = reservation.guests
        guest_word = get_guest_word(guests_count)
        formatted_time = reservation.time.strftime("%H:%M")
        today = date.today()
        tomorrow = today + timedelta(days=1)

        if reservation.date == today:
            reservation_message = f"На сегодня в {formatted_time} на {guests_count} {guest_word}."
        elif reservation.date == tomorrow:
            reservation_message = f"На завтра в {formatted_time} на {guests_count} {guest_word}."
        else:
            reservation_message = f"На {reservation.date.strftime('%d.%m.%Y')} в {formatted_time} на {guests_count} {guest_word}."

        reservation_data = {
            "name": reservation.customer_name,
            "date": reservation.date,
            "time": reservation.time,
            "guests": guests_count,
            "phone": reservation.customer_phone,
        }

    return form, success, reservation_data, reservation_message


def reserve_table(request, city_slug, place_slug):
    city = get_object_or_404(City, slug=city_slug)
    place = get_object_or_404(Place, slug=place_slug, city=city)

    form, success, reservation_data, reservation_message = handle_reservation(request, place)

    return render(request, "reservations/place_detail.html", {
        "place": place,
        "reservation_form": form,
        "reservation_successful": success,
        "reservation_data": reservation_data,
        "reservation_message": reservation_message,
        "selected_city": city,
    })


# ---------------- JSON API for Booking ----------------

def update_time_choices(request, place_id, date_str):
    place = get_object_or_404(Place, id=place_id)
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = selected_date.strftime("%a").upper()
    schedule = WorkSchedule.objects.filter(place=place, day=weekday).first()

    time_choices = []
    if schedule:
        start_time = schedule.open_time
        end_time = schedule.close_time
        if end_time < start_time:
            end_time = time(23, 59)

        interval = timedelta(minutes=place.booking_settings.booking_interval)
        unavailable_interval = timedelta(minutes=place.booking_settings.unavailable_interval)
        now = datetime.now()

        current_time = start_time
        if selected_date == now.date():
            next_available_time = now + unavailable_interval
            current_time = max(next_available_time.time(), start_time)
            current_time = (datetime.combine(datetime.today(), next_available_time.time()) + interval).time()

        while current_time <= end_time:
            time_choices.append(current_time.strftime("%H:%M"))
            current_time = (datetime.combine(datetime.today(), current_time) + interval).time()

    return JsonResponse({"time_choices": time_choices})


def check_open_status(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    selected_date_str = request.GET.get("date")
    if not selected_date_str:
        return JsonResponse({"error": "Invalid date"}, status=400)

    selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d")
    weekday = calendar.day_name[selected_date.weekday()]
    is_open = place.work_schedule.filter(day=weekday, is_closed=False).exists()
    return JsonResponse({"is_open": is_open})
