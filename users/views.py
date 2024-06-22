from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def user_profile(request):
    favorite_places = request.user.favorites.all()

    context = {
        'favorite_places': favorite_places,
    }
    return render(request, 'users/user_profile.html', context)
