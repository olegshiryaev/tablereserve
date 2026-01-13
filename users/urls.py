from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = "users"

urlpatterns = [
    # Вход
    path("login/", views.CustomLoginView.as_view(), name="account_login"),
    
    # Выход
    path("logout/", views.CustomLogoutView.as_view(), name="account_logout"),

    path("signup/", views.CustomSignupView.as_view(), name="account_signup"),
    
    # Профиль
    path("<int:id>/", views.ProfileDetailView.as_view(), name="profile"),
    path("edit/", views.ProfileUpdateView.as_view(), name="profile-edit"),
    
    # Избранное
    path("favorites/toggle/<int:place_id>/", views.toggle_favorite, name="toggle_favorite"),
    
    # Детали бронирования
    path("order/<int:pk>/", views.ReservationDetailView.as_view(), name="reservation-detail"),
]