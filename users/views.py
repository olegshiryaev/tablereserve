from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from reservations.models import Place
from users.models import Favorite


@login_required
def user_profile(request):
    favorite_places = request.user.favorites.all()

    context = {
        'favorite_places': favorite_places,
    }
    return render(request, 'users/user_profile.html', context)


@login_required
def add_to_favorites(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    user = request.user

    if not Favorite.objects.filter(user=user, place=place).exists():
        Favorite.objects.create(user=user, place=place)
        message = 'Заведение добавлено в избранное'
    else:
        message = 'Заведение уже добавлено в избранное'

    return JsonResponse({'message': message})

@login_required
def remove_from_favorites(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    user = request.user

    favorite = Favorite.objects.filter(user=user, place=place).first()
    if favorite:
        favorite.delete()
        message = 'Заведение удалено из избранного'
    else:
        message = 'Заведение не было добавлено в избранное'

    return JsonResponse({'message': message})
