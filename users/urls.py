from django.urls import path
from allauth.account.views import SignupView
from .views import (
    activate,
    custom_email_verification,
    toggle_favorite,
    user_profile,
)


app_name = "users"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="account_signup"),
    path("profile/", user_profile, name="user_profile"),
    path(
        "accounts/confirm-email/<str:key>/",
        custom_email_verification,
        name="custom_confirm_email",
    ),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("favorites/toggle/<int:place_id>/", toggle_favorite, name="toggle_favorite"),
]
