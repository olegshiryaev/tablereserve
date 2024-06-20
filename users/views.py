from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Place, Favorite

@require_POST
def toggle_favorite(request):
    place_id = request.POST.get('place_id')
    is_favorite = request.POST.get('is_favorite', False)

    try:
        place = Place.objects.get(id=place_id)
        user = request.user

        # Проверяем, существует ли уже запись в избранном для этого пользователя и заведения
        favorite, created = Favorite.objects.get_or_create(user=user, palce=place)

        if not is_favorite and not created:  # Если не в избранном и запись существует
            favorite.delete()
        elif is_favorite and created:  # Если в избранном и запись была создана
            pass  # Можно выполнить дополнительные действия при добавлении в избранное

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
