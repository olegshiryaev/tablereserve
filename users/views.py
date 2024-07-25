from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from reservations.models import Place
from users.models import CustomUser, Favorite

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


@login_required
def user_profile(request):
    favorite_places = request.user.favorites.all()

    context = {
        "favorite_places": favorite_places,
    }
    return render(request, "users/user_profile.html", context)


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
