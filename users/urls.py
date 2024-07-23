from django.urls import path
from .views import (
    activate,
    toggle_favorite,
    user_profile,
)


app_name = "users"

urlpatterns = [
    path("profile/", user_profile, name="user_profile"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("favorites/toggle/<int:place_id>/", toggle_favorite, name="toggle_favorite"),
]
