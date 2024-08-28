from django.urls import path
from allauth.account.views import SignupView
from .views import (
    ReservationDetailView,
    activate,
    custom_email_verification,
    ProfileUpdateView,
    ProfileDetailView,
    toggle_favorite,
)


app_name = "users"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="account_signup"),
    path("<int:id>/", ProfileDetailView.as_view(), name="profile"),
    path("edit/", ProfileUpdateView.as_view(), name="profile-edit"),
    path(
        "accounts/confirm-email/<str:key>/",
        custom_email_verification,
        name="custom_confirm_email",
    ),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("favorites/toggle/<int:place_id>/", toggle_favorite, name="toggle_favorite"),
    path(
        "order/<int:pk>/",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
]
