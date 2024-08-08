from django.urls import path
from allauth.account.views import SignupView
from .views import (
    activate,
    toggle_favorite,
    user_profile,
)


app_name = "users"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="account_signup"),
    path("profile/", user_profile, name="user_profile"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("favorites/toggle/<int:place_id>/", toggle_favorite, name="toggle_favorite"),
]
