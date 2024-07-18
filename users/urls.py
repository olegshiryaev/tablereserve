from django.urls import path
from .views import (
    toggle_favorite,
    user_profile,
)


app_name = "users"

urlpatterns = [
    path("profile/", user_profile, name="user_profile"),
    path("favorites/toggle/<int:place_id>/", toggle_favorite, name="toggle_favorite"),
]
