from django.urls import path
from .views import add_to_favorites, remove_from_favorites, user_profile


app_name = 'users'

urlpatterns = [
    path('profile/', user_profile, name='user_profile'),
    path('add_to_favorites/<int:place_id>/', add_to_favorites, name='add_to_favorites'),
    path('remove_from_favorites/<int:place_id>/', remove_from_favorites, name='remove_from_favorites'),
]