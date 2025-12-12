from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView
from django.contrib import messages
from django.utils import timezone

from reservations.models import Place, Reservation
from users.forms import ProfileForm
from users.models import CustomUser, Profile
from reservations.models import Favorite
from users.utils import time_since_last_seen

User = get_user_model()

class CustomLoginView(AuthLoginView):
    template_name = "account/login_modal.html"
    redirect_field_name = "next"

    def form_invalid(self, form):
        response = super().form_invalid(form)

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({"errors": errors}, status=400)

        return response


class ProfileDetailView(DetailView):
    """
    Представление для просмотра профиля
    """

    model = CustomUser
    context_object_name = "profile_user"
    template_name = "users/profile_detail.html"

    def get_object(self, queryset=None):
        # Получаем пользователя по id из URL
        user_id = self.kwargs.get("id")
        return get_object_or_404(CustomUser, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        context["profile_user"] = profile_user
        current_user = self.request.user

        # Проверяем, является ли текущий пользователь владельцем профиля
        is_owner = profile_user == current_user
        context["is_owner"] = is_owner

        # Получаем текущее время
        now = timezone.now()

        # Фильтрация бронирований
        filter_type = self.request.GET.get("filter", "current")

        if is_owner:
            if filter_type == "current":
                # Текущие бронирования
                reservations = profile_user.reservations.filter(
                    date__gt=now.date(),  # Бронирования на даты позже текущей
                    status__in=["confirmed", "pending"],
                ) | profile_user.reservations.filter(
                    date=now.date(),  # Бронирования на текущую дату с временем позже текущего
                    time__gte=now.time(),
                    status__in=["confirmed", "pending"],
                )
            elif filter_type == "past":
                # Прошедшие бронирования
                reservations = profile_user.reservations.filter(
                    date__lt=now.date(),  # Бронирования на даты раньше текущей
                    status__in=["confirmed", "pending"],
                ) | profile_user.reservations.filter(
                    date=now.date(),  # Бронирования на текущую дату с временем раньше текущего
                    time__lt=now.time(),
                    status__in=["confirmed", "pending"],
                )
            elif filter_type == "cancelled":
                # Отменённые бронирования
                reservations = profile_user.reservations.filter(
                    status__in=["cancelled_by_restaurant", "cancelled_by_customer"]
                )
            else:
                reservations = profile_user.reservations.all()

            # Добавляем бронирования в контекст
            context["reservations"] = reservations.order_by("-date", "-time")

            # Добавляем избранные места
            context["favorites"] = profile_user.favorites.prefetch_related(
                "place"
            ).all()

        # Всегда показываем отзывы
        reviews = profile_user.reviews.select_related("place", "place__type").filter(
            status="approved"
        )
        for review in reviews:
            if review.place and review.place.type:
                review.place_type_phrase = review.place.type.name
        context["reviews"] = reviews

        # Добавляем название страницы
        context["title"] = f"Страница пользователя: {profile_user.profile}"

        # Сообщение о последнем визите
        context["last_seen_message"] = time_since_last_seen(profile_user)

        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Представление для редактирования профиля
    """

    model = Profile
    form_class = ProfileForm
    template_name = "users/profile_edit.html"
    context_object_name = "profile"

    def get_success_url(self):
        return reverse("users:profile", kwargs={"id": self.request.user.id})

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["title"] = f"Редактирование профиля пользователя: {self.object}"
        return context


@require_POST
@login_required
def toggle_favorite(request, place_id):
    user = request.user
    try:
        place = Place.objects.get(id=place_id)
    except Place.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Place does not exist"}, status=404
        )

    favorite, created = Favorite.objects.get_or_create(user=user, place=place)

    if not created:
        favorite.delete()
        return JsonResponse({"status": "removed"})

    return JsonResponse({"status": "added"})


class ReservationDetailView(LoginRequiredMixin, DetailView):
    model = Reservation
    template_name = "users/reservation_detail.html"
    context_object_name = "reservation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation = self.get_object()

        # Получаем обложку заведения, если она существует
        cover_image = reservation.place.images.filter(is_cover=True).first()
        context["cover_image"] = cover_image

        return context
