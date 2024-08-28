from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from django.shortcuts import redirect, HttpResponse
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView

from reservations.models import Place, Reservation
from users.forms import ProfileForm
from users.models import CustomUser, Favorite, Profile

User = get_user_model()


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect("login")
    else:
        return render(request, "users/activation_invalid.html")


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """
    Представление для просмотра профиля
    """

    model = CustomUser
    context_object_name = "user"
    template_name = "users/profile_detail.html"

    def get_object(self, queryset=None):
        # Возвращает текущего пользователя
        return get_object_or_404(CustomUser, pk=self.request.user.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        # Добавляем дополнительные данные в контекст
        context["reservations"] = user.reservations.all()
        context["favorites"] = user.favorites.all()
        context["reviews"] = user.reviews.all()
        context["title"] = f"Страница пользователя: {user.profile.name}"
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
        context["title"] = (
            f"Редактирование профиля пользователя: {self.request.user.username}"
        )
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


def activate_account(request, email, token):
    user = get_object_or_404(CustomUser, email=email)
    if default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        # Перенаправление на страницу успешной активации
        return redirect("activation_success")
    else:
        # Обработка неудачной активации
        return redirect("activation_failed")


def custom_email_verification(request, key):
    """
    Представление для автоматического подтверждения email.
    """
    try:
        email_address = EmailAddress.objects.get(key=key)
        if email_address.verified:
            return HttpResponse("Email уже подтвержден.")

        # Подтверждаем email
        email_address.verified = True
        email_address.save()

        # Перенаправляем пользователя на нужную страницу после подтверждения
        return redirect(settings.ACCOUNT_EMAIL_CONFIRMATION_REDIRECT_URL)
    except EmailAddress.DoesNotExist:
        return HttpResponse("Неверный ключ подтверждения.")


class ReservationDetailView(LoginRequiredMixin, DetailView):
    model = Reservation
    template_name = "users/reservation_detail.html"
    context_object_name = "reservation"
